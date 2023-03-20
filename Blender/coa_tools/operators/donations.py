'''
Copyright (C) 2015 Andreas Esau
andreasesau@gmail.com

Created by Andreas Esau

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
    
import webbrowser
import bpy
from bpy.props import *

class COATOOLS_OT_Donate(bpy.types.Operator):
    bl_idname = "coa_operator.coa_donate"
    bl_label = "Donate"
    bl_description = "You like my Addon and would love to donate a portion. Feel free to so. Just follow this button."
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        webbrowser.open("https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=8TB6CNT9G8LEN")
        return {"FINISHED"}
    
class COATOOLS_OT_Tweet(bpy.types.Operator):
    bl_idname = "coa_operator.coa_tweet"
    bl_label = "Tweet this addon"
    bl_description = "You like this addon and want to share it with others. Just tweet it."
    bl_options = {"REGISTER"}
    
    link: StringProperty(default="")
    text: StringProperty(default="")
    hashtags: StringProperty(default="")
    via: StringProperty(default="")
    
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        #self.link = self.link.replace(" ","%")
        #webbrowser.open("https://twitter.com/intent/tweet?text=Check%out%#2DAnimTools%by%@ndee85")
        
        url = "https://twitter.com/intent/tweet?"
        if self.link != "":
            url += "&url="+self.link
        if self.text != "":    
            url += "&text="+self.text.replace(" ","+")
        if self.hashtags != "":    
            url += "&hashtags="+self.hashtags
        if self.via != "":
            url += "&via="+self.via
        #"https://twitter.com/intent/tweet?url=https://www.youtube.com/ndee85&text=Hello+World&hashtags=coatools,test&via=ndee85"    
        webbrowser.open(url)
        return {"FINISHED"}
            
        
        
        