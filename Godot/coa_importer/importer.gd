tool
extends EditorPlugin

var open_importer = null

var import_window_res = preload("import_dialog.tscn")
var import_window = null
var warning_dialog = null
var btn_load_json = null
var btn_dst_file = null
var src_dialog = null
var dst_dialog = null
var src_scene = null
var dst_scene = null

var label_src_scene = null
var label_dst_scene = null

var json_info = null
var bone_count = 0
var sprite_count = 0

var check_merge = null

var json_data = {}
var json_path = ""
var file_dst_path = ""

var dir
var root_node

func _init():
	print("PLUGIN INIT")

func _enter_tree():
	import_window = import_window_res.instance()
	import_window.connect("confirmed",self,"_create_imported_scene")


	json_info = import_window.get_node("VBoxContainer2/json_info/text")

	check_merge = import_window.get_node("VBoxContainer2/MarginContainer/check_merge_scenes")

	label_dst_scene = import_window.get_node("VBoxContainer2/HBoxContainer2/VBoxContainerFileNames/path_destination_file/label")
	label_src_scene = import_window.get_node("VBoxContainer2/HBoxContainer2/VBoxContainerFileNames/path_source_file/label")

	warning_dialog = import_window.get_node("warning_dialog")

	#src_dialog = import_window.get_node("file_source")
	src_dialog = EditorFileDialog.new()
	src_dialog.set_access(src_dialog.ACCESS_FILESYSTEM)
	src_dialog.set_mode(src_dialog.MODE_OPEN_FILE)
	src_dialog.add_filter("*.json")
	src_dialog.connect("file_selected",self,"_src_dialog_confirm")
	get_editor_interface().get_base_control().add_child(src_dialog)



	#dst_dialog = import_window.get_node("file_destination")
	dst_dialog = EditorFileDialog.new()
	dst_dialog.set_access(dst_dialog.ACCESS_RESOURCES)
	dst_dialog.set_mode(dst_dialog.MODE_SAVE_FILE)
	dst_dialog.add_filter("*.xml")
	dst_dialog.add_filter("*.tscn")
	dst_dialog.add_filter("*.scn")
	dst_dialog.connect("file_selected",self,"_dst_dialog_confirm")
	get_editor_interface().get_base_control().add_child(dst_dialog)


	get_editor_interface().get_base_control().add_child(import_window)
	import_window.get_ok().set_text("Import")
	btn_load_json = import_window.get_node("VBoxContainer2/HBoxContainer2/VBoxContainerButtons/button_source")
	btn_load_json.connect("pressed",self,"_open_src_dialog")

	btn_dst_file = import_window.get_node("VBoxContainer2/HBoxContainer2/VBoxContainerButtons/button_destination")
	btn_dst_file.connect("pressed",self,"_open_dst_dialog")



	open_importer = Button.new()
	open_importer.set_text("Import COA File")
	open_importer.connect("pressed",self,"_open_importer")
	#add_custom_control(CONTAINER_CANVAS_EDITOR_MENU,open_importer)
	add_control_to_container(CONTAINER_CANVAS_EDITOR_MENU, open_importer)


func _exit_tree():
	open_importer.free()
	open_importer = null

	import_window.free()
	import_window = null


### function to open the main importer window where source and destination files can be set
func _open_importer():
	### center window
	var pos = OS.get_window_size()*0.5 - import_window.get_rect().size*0.5
	print(pos)
	import_window.rect_position = pos

	json_info.clear()
	import_window.popup_centered()

	if json_path != "":
		_src_dialog_confirm(json_path)
	if file_dst_path != "":
		_dst_dialog_confirm(file_dst_path)


### this will open the dialog to load in the source json file
func _open_src_dialog():
	print("_open_src_dialog")
	#json_info.set_ignore_mouse(true)
	src_dialog.popup_centered_ratio()
	src_scene = null
	#src_dialog.set_pos(import_window.get_pos())
	src_dialog.set_current_dir(src_dialog.get_current_dir())

### once the src file dialog is confirmed this will load in the json file and prepare a log file with some information that is gathered from the json file
func _src_dialog_confirm(path):
	json_info.clear()
	#json_info.set_ignore_mouse(false)
	json_path = path
	var json = File.new()
	if json.file_exists(json_path):

		json.open(json_path,File.READ)
		json_data = parse_json(json.get_as_text())
		json.close()

		label_src_scene.set_text(json_path)

	dir = Directory.new()
	dir.open("res://")

	if src_scene != null:
		src_scene.free()
	src_scene = Node2D.new()
	src_scene.set_name(json_data["name"])
	write_log(json_info,"Json import File Information")
	json_info.newline()

	if "changelog" in json_data:
		write_log(json_info,"#### Changelog ####")
		for log_msg in json_data["changelog"]:
			write_log(json_info,str(log_msg))
		json_info.newline()
	write_log(json_info,"#### Node Information ####")
	write_log(json_info,str("Name: ",json_data["name"]))
	### import nodes and log
	sprite_count = 0
	bone_count = 0
	create_nodes(json_data["nodes"],src_scene,src_scene,false)
	write_log(json_info,str("Sprite Count: ",sprite_count),0)
	write_log(json_info,str("Bone Count:   ",bone_count),0)

	### import animations and log
	import_animations(json_data["animations"],src_scene)
	src_scene = src_scene


### this will open the dialog to say where to save the imported json file as godots scene file
func _open_dst_dialog():
	#json_info.set_ignore_mouse(true)
	dst_dialog.popup_centered_ratio()
	dst_scene = null
	#dst_dialog.set_pos(import_window.get_pos())
	dst_dialog.set_current_dir(dst_dialog.get_current_dir())

### this will load in the scene file if is selected with the destination file dialog and it sets the global path for the dst file
func _dst_dialog_confirm(path):
	#json_info.set_ignore_mouse(false)

	file_dst_path = path
	var file = File.new()
	label_dst_scene.set_text(file_dst_path)
	if file.file_exists(file_dst_path):

		var dst_scene_res = load(file_dst_path)
		dst_scene = dst_scene_res.instance()

### function to save a node scene to the destination path
func save_packed_scene(scene):
	if scene.has_node("AnimationPlayer"):
		scene.get_node("AnimationPlayer").clear_caches()

	# pack scene and save
	var outfile = PackedScene.new()
	outfile.pack(scene)
	ResourceSaver.save( file_dst_path, outfile)


### this function actually imports the json file
func _create_imported_scene():
	if file_dst_path != "" and json_path != "":

		### if destination scene exists already, transfer root node otherwise create Node2D
		if src_scene != null:
			src_scene.free()
		if dst_scene != null and check_merge.is_pressed():
			src_scene = Node2D.new()
			src_scene.replace_by(dst_scene)
		else:
			src_scene = Node2D.new()
		src_scene.set_name(json_data["name"])

		### Create all nodes from Json File
		create_nodes(json_data["nodes"],src_scene,src_scene)

		### Import all Animations
		if "animations" in json_data:
			import_animations(json_data["animations"],src_scene)
			src_scene = src_scene

		### if merging is enabled, make a clever update and preserve local changes, update imported nodes and delete not available nodes
		if dst_scene != null and check_merge.is_pressed():
			save_packed_scene(merge_scenes(src_scene,dst_scene))
			import_window.hide()
		### make a simple import and write all data into scene
		else:
			save_packed_scene(src_scene)
			import_window.hide()


		show_warning_dialog("Info","Import complete, please reload Scene.")
	else:
		show_warning_dialog()


### this function gets all children of a node and list them in an array
func get_child_recursive(node,child_list=[]):
	for child in node.get_children():
		child_list.append(child)
		if child.get_child_count() > 0:
			get_child_recursive(child,child_list)
	return child_list

### this function updates a node with another one. it will update all relevant node properties with the once to replace
func replace_node(node, replace_with):
	if node.get_class() == "Node2D" or node.get_class() == "Sprite":
		node.position = replace_with.position
		node.rotation_degrees = replace_with.rotation_degrees
		node.scale = replace_with.scale
		node.opacity = replace_with.opacity
		node.z_index = replace_with.z_index
		if node.get_class() == "Sprite":
			node.texture = replace_with.texture
			node.hframes = replace_with.hframes
			node.vframes = replace_with.vframes
			node.frame = replace_with.frame
			node.centered = replace_with.centered
			node.offset = replace_with.offset
	elif node.get_class() == "AnimationPlayer":
		### delete not available animations that are imported from blender
		var anim_list = node.get_animation_list()
		for anim in anim_list:
			if !(replace_with.has_animation(anim)) and anim in node.get_meta_list():
				node.set_meta(anim,false)
				node.remove_animation(anim)
				node.clear_caches()

		### update animations and add new animations
		anim_list = replace_with.get_animation_list()
		for anim in anim_list:
			if node.has_animation(anim):
				node.get_animation(anim).clear()
				node.clear_caches()
				node.remove_animation(anim)
			node.clear_caches()
			node.add_animation(anim,replace_with.get_animation(anim))

### gets only parent nodes in node list
func get_parent_nodes(list):
	var parent_list = []
	for node in list:
		if node.get_parent() != null:
#			if !(node.get_parent() in list):
				parent_list.append(node)
	return parent_list

### this will add nodes recursively
func add_node_recursive(node,owner,parent):
	if node.get_parent() == null:
		parent.add_child(node)
	node.set_owner(owner)
	if node.get_child_count() > 0:
		for child in node.get_children():
			add_node_recursive(child,owner,node)

### function to cleverly merge source and destination scene
func merge_scenes(src_scene,dst_scene):

	### delete nodes that are not available in the src scene anymore and are imported from blender
	var node_dst_scene = get_child_recursive(dst_scene)
	var to_be_deleted = []
	for node in node_dst_scene:
		if node != null:
			var node_path = dst_scene.get_path_to(node)
			if !(src_scene.has_node(node_path)) and node.has_meta("imported_from_blender"):
				to_be_deleted.append(node)
	for node in get_parent_nodes(to_be_deleted):
		node.free()

	### update nodes from src scene and add new nodes if they are not available
	var node_src_scene = get_child_recursive(src_scene)
	for node in node_src_scene:
		var node_path = src_scene.get_path_to(node)
		if dst_scene.has_node(node_path):
			var node2 = dst_scene.get_node(node_path)

			replace_node(node2,node)
		else:
			var new_nodes = node.duplicate()
			var parent_node = dst_scene.get_node(src_scene.get_path_to(node.get_parent()))
			add_node_recursive(new_nodes,dst_scene,parent_node)
	return dst_scene


### a function to write logs when loading in a json file
func write_log(text_field,msg,indent=0,line_break=false):
	text_field.push_indent(indent)
	if line_break:
		text_field.newline()
	text_field.add_text(msg)

### a dialog that displays given title and messages
func show_warning_dialog(title="",msg=""):
	warning_dialog.popup_centered()
	if msg != "":
		warning_dialog.set_text(msg)
	if title != "":
		warning_dialog.set_title(title)

	var pos = import_window.rect_position + import_window.get_rect().size*0.5 - warning_dialog.get_rect().size*0.5


### recursive function that looks up if a node has BONE nodes as children
func has_bone_child(node):
	if "children" in node:
		for item in node["children"]:
			if item["type"] == "BONE":
				return true
			if "children" in item:
				has_bone_child(item)
	return  false

### function to import animations -> this will create an AnimationPlayer Node and generate all animations with its tracks and values
func import_animations(animations,owner):
	var anim_player = AnimationPlayer.new()
	owner.add_child(anim_player)
	anim_player.set_owner(owner)
	anim_player.set_name("AnimationPlayer")

	write_log(json_info,str("Animation Count: ",animations.size()))
	if animations.size() > 0:
		write_log(json_info,str("#### Animations ####"),0,true)
	for anim in animations:
		anim_player.clear_caches()
		write_log(json_info,str("> ",anim["name"],":   length - ", anim["length"], "    fps - ", anim["fps"]))
		var anim_data = Animation.new()
		anim_data.set_loop(true)
		anim_data.set_length(anim["length"])
		for key in anim["keyframes"]:
			print("key " + key)
			var trackPath =  key
			# godot 3 redefined tramsorm attributes
			trackPath = trackPath.replace("transform/pos", "position")
			trackPath = trackPath.replace("transform/rot", "rotation_degrees")
			#trackPath = trackPath.replace("transform/scale:", "scale")
			print("trackPath " + trackPath)
			var track = anim["keyframes"][key]
			var idx = anim_data.add_track(Animation.TYPE_VALUE)
			anim_data.track_set_path(idx,trackPath)
			for time in track:
				var value = track[time]["value"]
				if typeof(value) == TYPE_ARRAY:
					if key.find("pos") != -1:
						anim_data.track_insert_key(idx,float(time),Vector2(value[0],value[1]))
					elif key.find("scale") != -1:
						anim_data.track_insert_key(idx,float(time),Vector2(value[0],value[1]))
					elif key.find("modulate") != -1:
						anim_data.track_insert_key(idx,float(time),Color(value[0],value[1],value[2],1.0))
				elif typeof(value) == TYPE_REAL:
					if key.find("rot") != -1:
						anim_data.track_insert_key(idx,float(time),rad2deg(value))
					else:
						anim_data.track_insert_key(idx,float(time),value)

				if key.find(":frame") != -1 or key.find(":z/z") != -1:
					anim_data.track_set_interpolation_type(idx, Animation.INTERPOLATION_NEAREST)
				else:
					anim_data.track_set_interpolation_type(idx, Animation.INTERPOLATION_LINEAR)
		anim_player.add_animation(anim["name"],anim_data)
		anim_player.set_meta(anim["name"],true)
		anim_player.clear_caches()

### this function generates the complete node structur that is stored in a json file. Generates SPRITE and BONE nodes.
func create_nodes(nodes,parent,subparent,copy_images=true,i=0):
	var dir2 = Directory.new()
	dir2.open("res://")
	for node in nodes:

		var new_node
		var offset = Vector2(0,0)
		if "offset" in node:
			offset = Vector2(node["offset"][0],node["offset"][1])
		if node["type"] == "BONE":
			bone_count += 1
			new_node = Node2D.new()
			new_node.set_meta("imported_from_blender",true)
			new_node.name = node["name"]
			new_node.position = Vector2(node["position"][0],node["position"][1])
			new_node.rotation_degrees = node["rotation"]
			new_node.scale = Vector2(node["scale"][0],node["scale"][1])
			new_node.z_index = node["z"]
			subparent.add_child(new_node)
			new_node.set_owner(parent)

			### handle bone drawing
			if new_node.get_parent() != null and node["bone_connected"]:
				new_node.set_meta("_edit_bone_",true)
			if !(has_bone_child(node)) or node["draw_bone"]:
				var draw_bone = Node2D.new()
				draw_bone.set_meta("_edit_bone_",true)
				draw_bone.name = str(node["name"],"_tail")
				draw_bone.position = Vector2(node["position_tip"][0],-node["position_tip"][1])
				draw_bone.hide()

				new_node.add_child(draw_bone)
				draw_bone.set_owner(parent)

		if node["type"] == "SPRITE":
			sprite_count += 1
			### copy images to destination folder
			new_node = Sprite.new()
			if copy_images:
				if json_path != "":
					var sprite_dir_path = file_dst_path.get_base_dir()

					if !(dir.dir_exists(str(sprite_dir_path,"/sprites"))):
						dir.make_dir(str(sprite_dir_path,"/sprites"))
					if dir.file_exists(str(json_path.get_base_dir(),"/",node["resource_path"])):
						var _src = str(json_path.get_base_dir(),"/",node["resource_path"])
						var _dst = str(sprite_dir_path,"/",node["resource_path"])
						dir.copy(_src,_dst)

						### set sprite texture
						new_node.set_texture(load(str(sprite_dir_path,"/",node["resource_path"])))

			new_node.set_meta("imported_from_blender",true)
			new_node.name = node["name"]
			new_node.hframes = node["tiles_x"]
			new_node.vframes = node["tiles_y"]
			new_node.frame = node["frame_index"]
			new_node.centered = false
			new_node.offset = Vector2(node["pivot_offset"][0],node["pivot_offset"][1])
			new_node.position = Vector2(node["position"][0]+offset[0],node["position"][1]+offset[0])
			new_node.rotation_degrees = node["rotation"]
			new_node.scale = Vector2(node["scale"][0],node["scale"][1])
			new_node.z_index = node["z"]

			subparent.add_child(new_node)
			new_node.set_owner(parent)

		if "children" in node and node["children"].size() > 0:
			i+=1
			create_nodes(node["children"],parent,new_node,copy_images,i)