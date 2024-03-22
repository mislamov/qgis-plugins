from qgis.core import QgsVectorLayer, QgsProject, QgsMessageLog
from qgis.utils import iface
from PyQt5.QtWidgets import QAction, QMessageBox, QFileDialog
import os

class GeoJSONStylePlugin:

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

    def initGui(self):
        # Создаем действие для плагина
        self.action = QAction('Загрузить geojson', self.iface.mainWindow())
        self.action.triggered.connect(self.check_geojson_style)
        self.iface.addPluginToMenu('Загрузить geojson', self.action)

    def unload(self):
        # Удаляем действие при выгрузке плагина
        self.iface.removePluginMenu('Загрузить geojson', self.action)

    def check_geojson_style(self):
        # Открыть диалог выбора файла GeoJSON
        file_dialog = QFileDialog()
        file_dialog.setNameFilters(["GeoJSON files (*.geojson)"])
        file_dialog.selectNameFilter("GeoJSON files (*.geojson)")
        file_dialog.setViewMode(QFileDialog.Detail)
        file_dialog.setFileMode(QFileDialog.ExistingFiles)  # Устанавливаем режим выбора нескольких файлов

        if file_dialog.exec_():
            filenames = file_dialog.selectedFiles()
            if filenames:
              for geojson_path in filenames:

                # Загрузка GeoJSON-файла
                layer = QgsVectorLayer(geojson_path, os.path.basename(geojson_path), 'ogr')

                # Проверка успешности загрузки
                if not layer.isValid():
                    QMessageBox.critical(None, "Error", "Failed to load layer from GeoJSON file.")
                    return

                # Получение параметра styleName
                style_name = None # layer.customProperty("styleName")
                if "SUCCEED" in geojson_path:
                   style_name = "SUCCEED.qml"
                if "FAILED" in geojson_path:
                   style_name = "FAILED.qml"
                if "PUBLISHED" in geojson_path:
                   style_name = "PUBLISHED.qml"

                if style_name:
                    # Применение стиля из плагина
                    self.apply_style(layer, style_name)
                else:
                    QMessageBox.warning(None, "Warning", "No styleName parameter found in GeoJSON file.")


    def apply_style(self, layer, style_name):
        # Применение стиля из плагина по указанному имени
        # Формирование полного пути к файлу стиля
        #style_path = QgsProject.instance().readPath("./") + "/" + style_name
        style_path = os.path.join(self.plugin_dir, style_name)

        print("style_path:" + style_path)
    
        # Проверка существования файла стиля
        if not os.path.exists(style_path):
            print("Style file '{}' does not exist.".format(style_path))
            QgsMessageLog.logMessage("Style file '{}' does not exist.".format(style_path), 'GeoJSONStylePlugin')
            return

        # Загрузка стиля из файла
        layer.loadNamedStyle(style_path)

        # Проверка успешности загрузки стиля
        if layer.renderer() is None:
            print("Failed to load style from file '{}'.".format(style_path))
            QgsMessageLog.logMessage("Failed to load style from file '{}'.".format(style_path), 'GeoJSONStylePlugin')
            return

        # Применение стиля к слою
        layer.triggerRepaint()
        print("Applied style '{}' to layer '{}'".format(style_name, layer.name()))
        QgsMessageLog.logMessage("Applied style '{}' to layer '{}'".format(style_name, layer.name()), 'GeoJSONStylePlugin')

        # Добавление слоя на карту
        QgsProject.instance().addMapLayer(layer)


def classFactory(iface):
    return GeoJSONStylePlugin(iface)
