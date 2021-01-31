#target Photoshop

var doc = app.activeDocument;
var layers = doc.layers;
var coords = [];
var exporter_version = "v1.0 Beta";

//Save Options for PNGs
var options = new ExportOptionsSaveForWeb();
options.format = SaveDocumentType.PNG;
options.PNG8 = false;
options.transparency = true;
options.optimized = true;

function deselect_all_layers() {   
    var desc01 = new ActionDescriptor();   
        var ref01 = new ActionReference();   
        ref01.putEnumerated( charIDToTypeID('Lyr '), charIDToTypeID('Ordn'), charIDToTypeID('Trgt') );   
    desc01.putReference( charIDToTypeID('null'), ref01 );   
    executeAction( stringIDToTypeID('selectNoLayers'), desc01, DialogModes.NO );
}

function write_dict_entry(tabs,key,value,comma){
    if(typeof(comma)==='undefined') var comma = true;
    
    var line = '';
    for(var i = 0; i < tabs*4;i++){
        line += ' ';
    }
    line += '"'+key+'": ';
    
    if (typeof(value) ==  "string"){
        line += '"';
    }else if(typeof(value) == "object"){
        line +='[';
    }
    
    line += value;
    
    if (typeof(value) ==  "string"){
        line += '"';
    }else if(typeof(value) == "object"){
        line +=']';
    }    
    if (comma){
        line += ',';
    }    
    return line;
}

function write_line(tabs,text){
    var line = '';
    for(var i = 0; i < tabs*4;i++){
        line += ' ';
    }
    line += text;
    return line;
}    

function save_coords(center_sprites,export_path, export_name){
    if (win.center_sprites.value){
        var offset = [doc.width.as("px")*-.5+','+doc.height.as("px")*.5];
    }else{
        var offset = [0,0];
    }    
    
    var json_file = new File(export_path+"/"+export_name+".json");
    json_file.open('w');
    
    json_file.writeln( write_line(tabs=0,'{'));
    json_file.writeln( write_dict_entry (tabs=1, "name", export_name));
    json_file.writeln( write_line (tabs=1, '"nodes": ['));
    
    for(var i = 0; i < coords.length; i++){
        json_file.writeln('        {');
        json_file.writeln( write_dict_entry( tabs = 3, key = "name", value = coords[i][0]));
        json_file.writeln( write_dict_entry( tabs = 3, key = "type", value = "SPRITE"));
        json_file.writeln( write_dict_entry( tabs = 3, key = "node_path", value = coords[i][0]));
        json_file.writeln( write_dict_entry( tabs = 3, key = "resource_path", value = "sprites/"+coords[i][0]));
        json_file.writeln( write_dict_entry( tabs = 3, key = "pivot_offset", value = [0,0]));
        json_file.writeln( write_dict_entry( tabs = 3, key = "offset", value = offset));
        json_file.writeln( write_dict_entry( tabs = 3, key = "position", value = [ coords[i][1][0],coords[i][1][2] ]));
        json_file.writeln( write_dict_entry( tabs = 3, key = "rotation", value = 0.0 ));
        json_file.writeln( write_dict_entry( tabs = 3, key = "scale", value = [1.0,1.0] ));
        json_file.writeln( write_dict_entry( tabs = 3, key = "opacity", value = 1.0 ));
        json_file.writeln( write_dict_entry( tabs = 3, key = "z", value = coords[i][1][1] ));
        json_file.writeln( write_dict_entry( tabs = 3, key = "tiles_x", value = coords[i][2][0] ));
        json_file.writeln( write_dict_entry( tabs = 3, key = "tiles_y", value = coords[i][2][1] ));
        json_file.writeln( write_dict_entry( tabs = 3, key = "frame_index", value = 0 ));
        json_file.writeln( write_dict_entry( tabs = 3, key = "children", value = [] , comma=false));
        if(i < coords.length-1){
            json_file.writeln(write_line(tabs=2,'},'));
        }else{
            json_file.writeln(write_line(tabs=2,'}'));
        }    
    }
    json_file.writeln(write_line(tabs=1,']'));
    json_file.writeln(write_line(tabs=0,'}'));
    json_file.close();
}

function flatten_layer(document,name){
// =======================================================
    var idMk = charIDToTypeID( "Mk  " );
        var desc54 = new ActionDescriptor();
        var idnull = charIDToTypeID( "null" );
            var ref47 = new ActionReference();
            var idlayerSection = stringIDToTypeID( "layerSection" );
            ref47.putClass( idlayerSection );
        desc54.putReference( idnull, ref47 );
        var idFrom = charIDToTypeID( "From" );
            var ref48 = new ActionReference();
            var idLyr = charIDToTypeID( "Lyr " );
            var idOrdn = charIDToTypeID( "Ordn" );
            var idTrgt = charIDToTypeID( "Trgt" );
            ref48.putEnumerated( idLyr, idOrdn, idTrgt );
        desc54.putReference( idFrom, ref48 );
        var idlayerSectionStart = stringIDToTypeID( "layerSectionStart" );
        desc54.putInteger( idlayerSectionStart, 161 );
        var idlayerSectionEnd = stringIDToTypeID( "layerSectionEnd" );
        desc54.putInteger( idlayerSectionEnd, 162 );
        var idNm = charIDToTypeID( "Nm  " );
        desc54.putString( idNm, name );
    executeAction( idMk, desc54, DialogModes.NO );
// =======================================================
    var idMrgtwo = charIDToTypeID( "Mrg2" );
    executeAction( idMrgtwo, undefined, DialogModes.NO );
    document.activeLayer.name = name;
}   

function extend_document_size(size_x, size_y){
// =======================================================
    var idCnvS = charIDToTypeID( "CnvS" );
        var desc8 = new ActionDescriptor();
        var idWdth = charIDToTypeID( "Wdth" );
        var idPxl = charIDToTypeID( "#Pxl" );
        desc8.putUnitDouble( idWdth, idPxl, size_x );
        var idHght = charIDToTypeID( "Hght" );
        var idPxl = charIDToTypeID( "#Pxl" );
        desc8.putUnitDouble( idHght, idPxl, size_y );
        var idHrzn = charIDToTypeID( "Hrzn" );
        var idHrzL = charIDToTypeID( "HrzL" );
        var idLeft = charIDToTypeID( "Left" );
        desc8.putEnumerated( idHrzn, idHrzL, idLeft );
        var idVrtc = charIDToTypeID( "Vrtc" );
        var idVrtL = charIDToTypeID( "VrtL" );
        var idTop = charIDToTypeID( "Top " );
        desc8.putEnumerated( idVrtc, idVrtL, idTop );
    executeAction( idCnvS, desc8, DialogModes.NO );
}    

function duplicate_into_new_doc(){
    // =======================================================
    var idMk = charIDToTypeID( "Mk  " );
        var desc231 = new ActionDescriptor();
        var idnull = charIDToTypeID( "null" );
            var ref114 = new ActionReference();
            var idDcmn = charIDToTypeID( "Dcmn" );
            ref114.putClass( idDcmn );
        desc231.putReference( idnull, ref114 );
        var idNm = charIDToTypeID( "Nm  " );
        desc231.putString( idNm, """dupli_layers_doc""" );
        var idUsng = charIDToTypeID( "Usng" );
            var ref115 = new ActionReference();
            var idLyr = charIDToTypeID( "Lyr " );
            var idOrdn = charIDToTypeID( "Ordn" );
            var idTrgt = charIDToTypeID( "Trgt" );
            ref115.putEnumerated( idLyr, idOrdn, idTrgt );
        desc231.putReference( idUsng, ref115 );
        var idVrsn = charIDToTypeID( "Vrsn" );
        desc231.putInteger( idVrsn, 5 );
    executeAction( idMk, desc231, DialogModes.NO );
}    

function export_sprites(export_path , export_name , crop_to_dialog_bounds , center_sprites, crop_layers, export_json){
    var init_units = app.preferences.rulerUnits;
    app.preferences.rulerUnits = Units.PIXELS;
    // check if folder exists. if not, create one
    var export_folder = new Folder(export_path+"/sprites");
    if(!export_folder.exists) export_folder.create();
    
    var tmp_layers = doc.layers;
    
    try{
        duplicate_into_new_doc();
        var dupli_doc = app.activeDocument;
    }catch(e){
        alert(e);
        win.close();
        return;
    }    
    
    /// deselect all layers and select first with this hack of adding a new layer and then deleting it again
    var testlayer = dupli_doc.artLayers.add();
    testlayer.remove();
    ///
    
    // flatten layers
    for(var i = 0; i < dupli_doc.layers.length; i++){ 
        var layer = dupli_doc.layers[i];
        dupli_doc.activeLayer = layer;
        if (layer.name.indexOf("--sprites") == -1){
            flatten_layer(dupli_doc,layer.name);
        }else if (layer.name.indexOf("--sprites") != -1 && layer.typename == "LayerSet") {
            for(var j = 0; j < layer.layers.length; j++){
                var sub_layer = layer.layers[j];
                dupli_doc.activeLayer = sub_layer;
                flatten_layer(dupli_doc,sub_layer.name);
            }    
        }
    }
    
    var selected_layer = dupli_doc.layers;
    for(var i = 0; i < selected_layer.length; i++){ 
        // deselect layers
        var layer = selected_layer[i];
        
        dupli_doc.activeLayer = layer;
        var bounds = [layer.bounds[0].as("px"),layer.bounds[1].as("px"),layer.bounds[2].as("px"),layer.bounds[3].as("px")];
        var bounds_width = bounds[2] - bounds[0];
        var bounds_height = bounds[3] - bounds[1];
        
        var layer_name = String(layer.name).split(' ').join('_');
        // get layer margin settings
        var margin = 0;
        if (layer_name.indexOf("m=") != -1){
            var margin_str_index = layer_name.indexOf("m=")+2;
            margin = Math.ceil(layer_name.substring(margin_str_index,layer_name.length));
        }
        var layer_pos = Array(bounds[0] - margin,-i,bounds[1] - margin);
        var tmp_doc = app.activeDocument;
        var tile_size = [1,1];
        var tmp_doc = app.documents.add( dupli_doc.width , dupli_doc.height , dupli_doc.resolution , layer_name , NewDocumentMode.RGB , DocumentFill.TRANSPARENT );
        
        // duplicate layer into new doc and crop to layerbounds with margin
        app.activeDocument = dupli_doc;
        layer.duplicate(tmp_doc , ElementPlacement.INSIDE);
        app.activeDocument = tmp_doc;
        var crop_bounds = bounds;
        
        if(crop_to_dialog_bounds == true){
            if(crop_bounds[0] < 0){ crop_bounds[0] = 0 };
            if(crop_bounds[1] < 0){ crop_bounds[1] = 0 };
            if(crop_bounds[2] > doc.width.as("px")){ crop_bounds[2] = doc.width.as("px")};
            if(crop_bounds[3] > doc.height.as("px")){ crop_bounds[3] = doc.height.as("px")};
        }
    
        crop_bounds[0] -= margin;
        crop_bounds[1] -= margin;
        crop_bounds[2] += margin;
        crop_bounds[3] += margin;
        
        if (crop_layers == true){
            tmp_doc.crop(crop_bounds);
        }    
        
        // check if layer is a group with sprite setting
        if (layer_name.indexOf("--sprites") != -1){
            var keyword_pos = layer_name.indexOf("--sprites") ;
            var sprites = tmp_doc.layers[0].layers;
            var sprite_count = sprites.length;
            if (column_str_index = layer_name.indexOf("c=") != -1){
                var column_str_index = layer_name.indexOf("c=")+2;
                var columns = Math.ceil(layer_name.substring(column_str_index,layer_name.length));
            }else{
                var columns = Math.ceil((Math.sqrt(sprite_count)));
            }
            tile_size = [columns,Math.ceil(sprite_count/columns)];
            var k = 0;
            for(var j = 0;j<sprites.length;j++){
                if(j>0 && j%columns == 0){
                    k = k+1;
                }
                sprites[j].translate(tmp_doc.width * (j%columns), tmp_doc.height * k);
            }
            
            
            extend_document_size(tmp_doc.width * columns, tmp_doc.height * (k+1));
        }
        
        // create layer name -> cut off commands
        var keyword_pos = 100000;
        if (layer_name.indexOf("--sprites") != -1){
            if (layer_name.indexOf("--sprites") < keyword_pos){
                keyword_pos = layer_name.indexOf("--sprites");
            }
        }
        if (layer_name.indexOf("c=") != -1){
            if (layer_name.indexOf("c=") < keyword_pos){
                keyword_pos = layer_name.indexOf("c=");
            }
        }
        if (layer_name.indexOf("m=") != -1){
            if (layer_name.indexOf("m=") < keyword_pos){
                keyword_pos = layer_name.indexOf("m=");
            }
        }
        if (layer_name[keyword_pos - 1] == "_"){
            layer_name = layer_name.substring(0,keyword_pos - 1);
        }else{
            layer_name = layer_name.substring(0,keyword_pos);
        }
        
        // do save stuff
        tmp_doc.exportDocument(File(export_path+"/sprites/"+layer_name+".png"),ExportType.SAVEFORWEB,options );
        
        // store coords
        coords.push([layer_name+".png",layer_pos,tile_size]);
        
        // close tmp doc again
        tmp_doc.close(SaveOptions.DONOTSAVECHANGES);
    }
    dupli_doc.close(SaveOptions.DONOTSAVECHANGES);
    
    if (export_json == true){
        save_coords(center_sprites,export_path, export_name);
    }    
    app.preferences.rulerUnits = init_units;
} 

function export_button(){

    win.export_name.text = String(win.export_name.text).split(' ').join('_');
    app.activeDocument.info.caption = win.export_path.text;
    app.activeDocument.info.captionWriter = win.export_name.text;
    //export_sprites(win.export_path.text, win.export_name.text, win.limit_layer.value, win.center_sprites.value);
    app.activeDocument.suspendHistory("Export selected Sprites","export_sprites(win.export_path.text, win.export_name.text, win.limit_layer.value, win.center_sprites.value,win.crop_layers.value,win.export_json.value)");
    win.close();
}    

function path_button(){
    var folder_path = Folder.selectDialog ("Select Place to save");
    if (folder_path != null){
        win.export_path.text = folder_path;
        app.activeDocument.info.caption = folder_path;
    }
}    

var win = new Window("dialog", 'Json Exporter'+exporter_version, [0,0,445,157], );
with(win){
	win.export_path = add( "edittext", [85,15,365,35], undefined );
	win.sText = add( "statictext", [5,20,75,40], 'Export Path:' );
	win.limit_layer = add( "checkbox", [5,70,180,90], 'Limit layers by Document' );
	win.center_sprites = add( "checkbox", [5,110,180,130], 'Center Sprites in Blender' );
	win.export_button = add( "button", [340,130,440,152], 'Export Layers' );
	win.export_name = add( "edittext", [85,40,440,60], undefined );
	win.sText2 = add( "statictext", [5,45,85,65], 'Export Name:' );
	win.button_path = add( "button", [370,13,440,35], 'select' );
	win.export_json = add( "checkbox", [5,130,180,150], 'Export Json File' );
	win.crop_layers = add( "checkbox", [5,90,180,110], 'Crop Layers' );
	}
if (app.activeDocument.info.caption != ''){
    win.export_path.text = app.activeDocument.info.caption;
    }else{
    win.export_path.text = app.activeDocument.path;    
    }
if (app.activeDocument.info.captionWriter != ''){
    win.export_name.text = app.activeDocument.info.captionWriter;
    }else{
    win.export_name.text = app.activeDocument.name.split('.')[0];
    }
win.export_button.onClick = export_button;
win.button_path.onClick = path_button;
win.center_sprites.value = true;
win.limit_layer.value = true;
win.crop_layers.value = true;
win.export_json.value = true;
win.center();
win.show();
