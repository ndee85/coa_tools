from PyQt5 import QtCore, QtGui, QtWidgets
from krita import *

import os
import json
from collections import OrderedDict

class COAToolsDocker(DockWidget):

    def __init__(self):
        super().__init__()
        # self.COAToolsExporter = COAToolsExporter()
        self.generateUi()
        ### exporter variables
        self.app = Application
        self.doc = self.app.activeDocument()

        self.storedData = {"COA_TOOLS_DATA": "", "export_path": "", "export_name": ""}

        # self.exportPath = "C:/Users/g041481/Desktop/tmp/krita_export"
        self.coaObjectName = "test"
        self.coaObject = OrderedDict({"name": "", "nodes": []})
        self.coaNode = OrderedDict({
            "name": "",
            "type": "SPRITE",
            "node_path": "file.png",
            "resource_path": "sprites/file.png",
            "pivot_offset": [0, 0],
            "offset": [0, 0],
            "position": [0, 0],
            "rotation": 0,
            "scale": [1, 1],
            "opacity": [0, 0],
            "z": 0,
            "tiles_x": 1,
            "tiles_y": 1,
            "frame_index": 0,
            "children": []})

    def alert(self, message):
        QtWidgets.QMessageBox.about(self, "Alert", str(message))

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "COA Tools Exporter"))
        self.label.setText(_translate("Form", "Export Path"))
        self.label_2.setText(_translate("Form", "Export Name"))
        self.exportButton.setText(_translate("Form", "Export Selected Sprites"))
        self.selectPathButton.setText(_translate("Form", "Select"))

    def exportDataToLayerName(self):
        self.doc = self.app.activeDocument()
        if self.doc != None and self.doc.rootNode() != None:
            if self.storedData["export_name"] != "" and self.storedData["export_path"] != "":
                dataNode = None
                for node in self.doc.rootNode().childNodes():
                    if "COA_TOOLS_DATA" in node.name():
                        dataNode = node

                if dataNode == None:
                    dataNode = self.doc.createNode(json.dumps(self.storedData), "paintlayer")
                    self.doc.rootNode().addChildNode(dataNode, None)
                else:
                    dataNode.setName(json.dumps(self.storedData))
                dataNode.setVisible(False)

    def layerNameToExportData(self):
        if self.doc != None and self.doc.rootNode() != None:
            dataNode = None
            for node in self.doc.rootNode().childNodes():
                if "COA_TOOLS_DATA" in node.name():
                    dataNode = node

            if dataNode != None:
                self.storedData = json.loads(dataNode.name())
                self.exportName.setText(self.storedData["export_name"])
                self.exportPath.setText(self.storedData["export_path"])
            else:
                self.exportName.setText("")
                self.exportPath.setText("")
        else:
            self.exportName.setText("")
            self.exportPath.setText("")

    def selectPath(self):
        self.doc = self.app.activeDocument()
        self.exportPath.setText(QtWidgets.QFileDialog.getExistingDirectory(self, "Select Export Directory"))
        self.storedData["export_path"] = self.exportPath.text()
        self.exportDataToLayerName()

    def textExportNameChanged(self, text):
        self.storedData["export_name"] = text
        self.exportDataToLayerName()

    def textExportPathChanged(self, text):
        self.storedData["export_path"] = text
        self.exportDataToLayerName()

    def generateUi(self):
        self.setWindowTitle("COA Tools Exporter")
        Form = QtWidgets.QWidget(self)

        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(Form)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.label = QtWidgets.QLabel(Form)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.label_2 = QtWidgets.QLabel(Form)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.exportName = QtWidgets.QLineEdit(Form)
        self.exportName.setObjectName("exportName")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.exportName)
        self.exportButton = QtWidgets.QPushButton(Form)
        self.exportButton.setObjectName("exportButton")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.exportButton)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.exportPath = QtWidgets.QLineEdit(Form)
        self.exportPath.setObjectName("exportPath")
        self.horizontalLayout.addWidget(self.exportPath)
        self.selectPathButton = QtWidgets.QPushButton(Form)
        self.selectPathButton.setObjectName("selectPathButton")
        self.horizontalLayout.addWidget(self.selectPathButton)
        self.formLayout.setLayout(0, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout)
        self.horizontalLayout_2.addLayout(self.formLayout)

        self.retranslateUi(Form)
        self.setWidget(Form)

        self.selectPathButton.clicked.connect(self.selectPath)
        self.exportButton.clicked.connect(self.export)
        self.exportName.textChanged.connect(self.textExportNameChanged)
        self.exportPath.textChanged.connect(self.textExportPathChanged)


    def canvasChanged(self, canvas):
        self.doc = Application.activeDocument()
        self.layerNameToExportData()

    def export(self):
        self.coaObject = OrderedDict({"name": "", "nodes": []})
        self.app = Application
        self.doc = self.app.activeDocument()

        if self.doc == None:
            QtWidgets.QMessageBox.about(self, "Warning", "First open or create a Document to export from.")
            return

        if self.exportPath.text() != "" and self.exportName.text() != "":
            self.exportSelectedNodes(self.exportPath.text(), self.exportName.text())
            QtWidgets.QMessageBox.about(self, "Info", "Exported finished.")
        else:
            QtWidgets.QMessageBox.about(self,"Warning", "Please select an Export Path and Name.")


    def exportSelectedNodes(self, exportPath, coaObjectName):
        selectedNodes = self.app.activeWindow().activeView().selectedNodes()

        jsonData = self.coaObject
        jsonData["name"] = coaObjectName

        ### create destination directory if not existent
        spritesPath = os.path.join(exportPath, "sprites")
        if not os.path.exists(spritesPath):
            os.makedirs(spritesPath)

            ### loop over selected nodes and export
        for i, node in enumerate(selectedNodes):
            name = node.name() + ".png"
            name = name.replace(" ", "_")
            name = name.lower()
            path = os.path.join(spritesPath, name)

            newCoaNode = OrderedDict(self.coaNode)
            newCoaNode["name"] = name
            newCoaNode["path"] = name
            newCoaNode["node_path"] = name
            newCoaNode["resource_path"] = "sprites/" + name
            newCoaNode["offset"] = [int(-self.doc.width() / 2), int(self.doc.height() / 2)]
            newCoaNode["position"] = [node.bounds().x(), node.bounds().y()]
            newCoaNode["z"] = len(selectedNodes) - i - 1

            jsonData["nodes"].append(newCoaNode)

            self.exportNode(node, path)

        ### write json data
        jsonPath = os.path.join(exportPath, coaObjectName + ".json")
        jsonFile = json.dumps(jsonData, indent="\t", sort_keys=False)
        textFile = open(jsonPath, "w")
        textFile.write(jsonFile)
        textFile.close()

    def exportNode(self, node, path):
        ### get pixel data of given node
        pixelData = node.projectionPixelData(node.bounds().x(), node.bounds().y(), node.bounds().width(),
                                             node.bounds().height())

        ### create new doc with dimensions of node
        newDoc = self.app.createDocument(node.bounds().width(), node.bounds().height(), node.name(), "RGBA", "U8", "",
                                         300.0)

        ### paste pixel data into layer of new document
        newNode = newDoc.rootNode().childNodes()[0]
        newNode.setPixelData(pixelData, 0.0, 0.0, node.bounds().width(), node.bounds().height())
        newNode.setOpacity(255)
        newDoc.refreshProjection()

        # app.activeWindow().addView(newDoc) # adds the document to view

        ### delete file if already exists
        if os.path.isfile(path):
            os.unlink(path)

        ### silent export of node
        newDoc.setBatchmode(True)
        newDoc.saveAs(path)
        newDoc.close()



Krita.instance().addDockWidgetFactory(DockWidgetFactory("COAToolsDocker", DockWidgetFactoryBase.DockRight, COAToolsDocker))