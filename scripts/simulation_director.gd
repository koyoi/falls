extends Node2D

const RUNTIME_DIR := "res://runtime"
const PRESET_PATH := RUNTIME_DIR + "/preset.json"
const FORCEFIELD_PATH := RUNTIME_DIR + "/forcefield.json"
const SEQUENCE_PATH := RUNTIME_DIR + "/sequence.json"
const CAPTURE_PATH := RUNTIME_DIR + "/capture.json"
const OBSTACLE_MASK_PATH := RUNTIME_DIR + "/obstacles_mask.png"
const WATCH_INTERVAL := 0.5
const MAX_PARTICLE_AMOUNT := 200000
const MAX_SPEED := 2000.0
const MAX_GRAVITY := 4096.0
const MAX_BLOOM := 2.0

var _preset_data: Dictionary = {}
var _forcefield_data: Dictionary = {}
var _sequence_data: Dictionary = {}
var _capture_data: Dictionary = {}

var _file_mtimes: Dictionary = {}
var _watch_accum := 0.0
var _sequence_time := 0.0
var _sequence_index := 0
var _sequence_duration := 0.0
var _force_time := 0.0

var _current_force := Vector2.ZERO
var _pending_capture := false
var _capture_delay_frames := 0
var _capture_request: Dictionary = {}
var _obstacle_texture: Texture2D

@onready var particle_process: ParticleProcess2D = get_node_or_null("ParticleEmitter")
@onready var background_rect: ColorRect = get_node_or_null("Background")
@onready var forcefield_node: Node2D = get_node_or_null("ForceField")

func _ready() -> void:
    _load_all_files()
    _prime_watch_times()
    set_process(true)

func _process(delta: float) -> void:
    _update_file_watch(delta)
    _update_sequence(delta)
    _force_time += delta
    _update_force_field()
    _update_capture()

func _load_all_files() -> void:
    _load_preset(PRESET_PATH)
    _load_forcefield(FORCEFIELD_PATH)
    _load_sequence(SEQUENCE_PATH)
    _load_capture(CAPTURE_PATH)
    _load_obstacle_mask()

func _prime_watch_times() -> void:
    for path in [PRESET_PATH, FORCEFIELD_PATH, SEQUENCE_PATH, CAPTURE_PATH, OBSTACLE_MASK_PATH]:
        if FileAccess.file_exists(path):
            _file_mtimes[path] = FileAccess.get_modified_time(path)

func _update_file_watch(delta: float) -> void:
    _watch_accum += delta
    if _watch_accum < WATCH_INTERVAL:
        return
    _watch_accum = 0.0
    for path in [PRESET_PATH, FORCEFIELD_PATH, SEQUENCE_PATH, CAPTURE_PATH, OBSTACLE_MASK_PATH]:
        var exists := FileAccess.file_exists(path)
        var had_previous := _file_mtimes.has(path)
        if not exists:
            if had_previous:
                _file_mtimes.erase(path)
                _on_runtime_file_removed(path)
            continue
        var mtime := FileAccess.get_modified_time(path)
        var previous := _file_mtimes.get(path, -1)
        if mtime != previous:
            _file_mtimes[path] = mtime
            _on_runtime_file_changed(path)

func _on_runtime_file_changed(path: String) -> void:
    match path:
        PRESET_PATH:
            _load_preset(path)
        FORCEFIELD_PATH:
            _load_forcefield(path)
        SEQUENCE_PATH:
            _load_sequence(path)
        CAPTURE_PATH:
            _load_capture(path)
        OBSTACLE_MASK_PATH:
            _load_obstacle_mask()

func _on_runtime_file_removed(path: String) -> void:
    match path:
        PRESET_PATH:
            _preset_data.clear()
            _apply_preset()
        FORCEFIELD_PATH:
            _forcefield_data.clear()
            _reset_force_timeline()
        SEQUENCE_PATH:
            _sequence_data.clear()
            _sequence_time = 0.0
            _sequence_index = 0
        CAPTURE_PATH:
            _capture_data.clear()
            _pending_capture = false
            _capture_delay_frames = 0
            _capture_request.clear()
        OBSTACLE_MASK_PATH:
            _clear_obstacle_texture()

func _load_json(path: String) -> Dictionary:
    var result: Dictionary = {}
    if not FileAccess.file_exists(path):
        push_warning("Runtime file not found: %s" % path)
        return result
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        push_warning("Failed to open runtime file: %s" % path)
        return result
    var parsed := JSON.parse_string(file.get_as_text())
    if typeof(parsed) != TYPE_DICTIONARY:
        push_warning("Invalid JSON object in %s" % path)
        return result
    return parsed

func _load_preset(path: String) -> void:
    _preset_data = _load_json(path)
    _apply_preset()

func _load_forcefield(path: String) -> void:
    _forcefield_data = _load_json(path)
    _reset_force_timeline()

func _load_sequence(path: String) -> void:
    _sequence_data = _load_json(path)
    _sequence_time = 0.0
    _sequence_index = 0
    var tracks := _sequence_data.get("tracks", [])
    if tracks is Array and not tracks.is_empty():
        _sequence_duration = float(tracks[-1].get("t", 0.0))
    else:
        _sequence_duration = 0.0


func _load_obstacle_mask() -> void:
    if not FileAccess.file_exists(OBSTACLE_MASK_PATH):
        _clear_obstacle_texture()
        return
    var image := Image.new()
    var err := image.load(OBSTACLE_MASK_PATH)
    if err != OK:
        push_warning("Failed to load obstacle mask: %s" % OBSTACLE_MASK_PATH)
        _clear_obstacle_texture()
        return
    _obstacle_texture = ImageTexture.create_from_image(image)
    if particle_process != null:
        particle_process.set_meta("obstacle_texture", _obstacle_texture)

func _clear_obstacle_texture() -> void:
    _obstacle_texture = null
    if particle_process == null:
        return
    if particle_process.has_meta("obstacle_texture"):
        particle_process.remove_meta("obstacle_texture")
    if particle_process.has_meta("obstacle_mask"):
        particle_process.remove_meta("obstacle_mask")
func _load_capture(path: String) -> void:
    _capture_data = _load_json(path)
    if _capture_data.is_empty():
        return
    _pending_capture = true
    _capture_delay_frames = 2
    _capture_request = _capture_data.get("capture", {})
    if particle_process != null and _capture_data.has("seed"):
        _set_property_if_present(particle_process, "seed", int(_capture_data.get("seed")))

func _apply_preset() -> void:
    if particle_process == null:
        return
    var emitter := _preset_data.get("emitter", {})
    if emitter is Dictionary:
        var rate := float(emitter.get("rate_per_sec", 0.0))
        rate = clamp(rate, 0.0, float(MAX_PARTICLE_AMOUNT))
        _set_property_if_present(particle_process, "amount", int(rate))
        particle_process.emitting = rate > 0.0
        if emitter.has("random_seed"):
            _set_property_if_present(particle_process, "seed", int(emitter.get("random_seed")))
    var motion := _preset_data.get("motion", {})
    if motion is Dictionary:
        var gravity := float(motion.get("gravity", 0.0))
        gravity = clamp(gravity, -MAX_GRAVITY, MAX_GRAVITY)
        var drag := float(motion.get("drag", 0.0))
        drag = clamp(drag, 0.0, 10.0)
        var sway := motion.get("sway", {})
        var sway_amp := 0.0
        var sway_freq := 0.0
        if sway is Dictionary:
            sway_amp = clamp(float(sway.get("amp", 0.0)), 0.0, 360.0)
            sway_freq = clamp(float(sway.get("freq", 0.0)), 0.0, 10.0)
        var mat := _ensure_particle_material()
        if mat != null:
            _set_property_if_present(mat, "gravity", Vector3(0.0, gravity, 0.0))
            _set_property_if_present(mat, "linear_damp", drag)
            _set_property_if_present(mat, "orbit_velocity", sway_amp)
            _set_property_if_present(mat, "orbit_velocity_random", sway_freq)
    var appearance := _preset_data.get("appearance", {})
    if appearance is Dictionary:
        _apply_palette(appearance.get("palette", []))
        var size := appearance.get("size_px", {})
        if size is Dictionary:
            var min_size := clamp(float(size.get("min", 2.0)), 0.5, 128.0)
            var max_size := clamp(float(size.get("max", min_size)), min_size, 256.0)
            var mat2 := _ensure_particle_material()
            if mat2 != null:
                _set_property_if_present(mat2, "scale_min", min_size / 32.0)
                _set_property_if_present(mat2, "scale_max", max_size / 32.0)
    var fx := _preset_data.get("fx", {})
    if fx is Dictionary and background_rect != null:
        var bg := fx.get("background", {})
        if bg is Dictionary:
            var gradient := bg.get("gradient", [])
            if gradient is Array and gradient.size() > 0:
                background_rect.color = Color(gradient[0])
        var bloom := clamp(float(fx.get("bloom", 0.0)), 0.0, MAX_BLOOM)
        if forcefield_node != null:
            forcefield_node.set_meta("bloom", bloom)
    var obstacle := _preset_data.get("obstacle", {})
    if obstacle is Dictionary:
        var mask_path := str(obstacle.get("collide_mask", ""))
        if mask_path != "":
            particle_process.set_meta("obstacle_mask", mask_path)
        var stickiness := clamp(float(obstacle.get("stickiness", 0.0)), 0.0, 1.0)
        particle_process.set_meta("obstacle_stickiness", stickiness)

func _apply_palette(palette: Variant) -> void:
    if particle_process == null:
        return
    if not (palette is Array) or palette.is_empty():
        return
    var gradient := Gradient.new()
    var steps := max(1, palette.size() - 1)
    for i in range(palette.size()):
        var color_str := str(palette[i])
        var t := float(i) / float(steps)
        gradient.add_point(t, Color(color_str))
    var texture := GradientTexture1D.new()
    texture.gradient = gradient
    _set_property_if_present(particle_process, "texture", texture)

func _ensure_particle_material() -> ParticleProcessMaterial:
    if particle_process == null:
        return null
    var mat := particle_process.process_material
    if mat == null or not (mat is ParticleProcessMaterial):
        mat = ParticleProcessMaterial.new()
        particle_process.process_material = mat
    return mat

func _set_property_if_present(obj: Object, property: String, value: Variant) -> void:
    if obj == null:
        return
    for prop in obj.get_property_list():
        if prop.get("name", "") == property:
            obj.set(property, value)
            return

func _reset_force_timeline() -> void:
    _current_force = Vector2.ZERO
    _force_time = 0.0
    if forcefield_node != null:
        forcefield_node.set_meta("force", _current_force)

func _update_force_field() -> void:
    var timeline := _forcefield_data.get("timeline", [])
    if not (timeline is Array) or timeline.is_empty():
        return
    var now := _force_time
    var active_event: Dictionary = {}
    for event in timeline:
        if not (event is Dictionary):
            continue
        var t := float(event.get("t", 0.0))
        if now >= t:
            active_event = event
        else:
            break
    if active_event.is_empty():
        return
    var speed := clamp(float(active_event.get("speed", 0.0)), 0.0, MAX_SPEED)
    var dir := float(active_event.get("dir_deg", 0.0))
    var dir_rad := deg_to_rad(dir)
    var force := Vector2.RIGHT.rotated(dir_rad) * speed
    var dur := float(active_event.get("dur", 0.0))
    if dur > 0.0 and now > float(active_event.get("t", 0.0)) + dur:
        force = Vector2.ZERO
    _current_force = force
    if forcefield_node != null:
        forcefield_node.set_meta("force", force)
    _apply_force_to_particles(force)

func _apply_force_to_particles(force: Vector2) -> void:
    var mat := _ensure_particle_material()
    if mat == null:
        return
    var direction := Vector3(force.x, force.y, 0.0)
    if direction.length() > 0.0:
        direction = direction.normalized()
    _set_property_if_present(mat, "direction", direction)
    _set_property_if_present(mat, "linear_accel", clamp(force.length(), 0.0, MAX_SPEED))

func _update_sequence(delta: float) -> void:
    _sequence_time += delta
    if _sequence_data.is_empty():
        return
    var tracks := _sequence_data.get("tracks", [])
    if not (tracks is Array) or tracks.is_empty():
        return
    while _sequence_index < tracks.size() and _sequence_time >= float(tracks[_sequence_index].get("t", 0.0)):
        _apply_sequence_event(tracks[_sequence_index])
        _sequence_index += 1
    var loop_enabled := bool(_sequence_data.get("loop", false))
    if loop_enabled and _sequence_duration > 0.0 and _sequence_time > _sequence_duration:
        _sequence_time = fmod(_sequence_time, _sequence_duration)
        _sequence_index = 0

func _apply_sequence_event(event: Dictionary) -> void:
    var apply := event.get("apply", {})
    if not (apply is Dictionary):
        return
    if apply.has("preset"):
        var preset_path := _resolve_runtime_path(str(apply.get("preset")))
        _load_preset(preset_path)
    if apply.has("force"):
        var force_path := _resolve_runtime_path(str(apply.get("force")))
        _load_forcefield(force_path)

func _resolve_runtime_path(file_name: String) -> String:
    if file_name.begins_with("res://"):
        return file_name
    return RUNTIME_DIR + "/" + file_name

func _update_capture() -> void:
    if not _pending_capture:
        return
    if _capture_delay_frames > 0:
        _capture_delay_frames -= 1
        return
    _pending_capture = false
    _perform_capture()

func _perform_capture() -> void:
    if _capture_request.is_empty():
        return
    var type := str(_capture_request.get("type", "image")).to_lower()
    var width := int(clamp(float(_capture_request.get("w", 1280)), 64.0, 8192.0))
    var height := int(clamp(float(_capture_request.get("h", 720)), 64.0, 8192.0))
    var output_name := str(_capture_request.get("output", "capture.png"))
    output_name = output_name.replace("..", "_")
    if output_name == "":
        output_name = "capture.png"
    var output_path := "user://out/" + output_name
    DirAccess.make_dir_recursive_absolute("user://out")
    var viewport := get_viewport()
    if viewport == null:
        return
    viewport.size = Vector2i(width, height)
    var texture := viewport.get_texture()
    if texture == null:
        push_warning("Viewport texture unavailable for capture.")
        return
    var image := texture.get_image()
    if image == null:
        push_warning("Unable to capture viewport image.")
        return
    if type == "image" or type == "screenshot":
        var err := image.save_png(output_path)
        if err != OK:
            push_warning("Failed to save capture to %s" % output_path)
    else:
        var frames := int(clamp(float(_capture_request.get("frames", 1)), 1.0, 600.0))
        for i in range(frames):
            var frame_name := output_path.get_basename() + "_%04d.png" % i
            image.save_png(frame_name)

func request_capture_now() -> void:
    _pending_capture = true
    _capture_delay_frames = 2
