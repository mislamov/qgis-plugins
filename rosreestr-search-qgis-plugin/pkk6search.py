# -*- coding: utf-8 -*-
# Rosreestr-search-qgis-plugin
# Licensed under the terms of GNU GPL 2
# Thanks to Martin Dobias for the 'QGIS Minimalist Plugin Skeleton'

import os
import ssl
import urllib.request
from osgeo import gdal
import re
import requests
import json
import math

from PyQt5.QtWidgets import (
    QInputDialog,
    QAction,
    QMessageBox
)   
from PyQt5.QtGui import QCursor

from qgis.gui import QgsMapTool

from qgis.PyQt.QtGui import QIcon
from qgis.utils import iface
from qgis.core import (
    QgsPointXY,
    QgsVectorLayer,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform
)
from qgis.core import QgsApplication
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt


from qgis.core import QgsMarkerSymbol
from qgis.core import QgsSimpleMarkerSymbolLayer
from qgis.core import QgsFeature, QgsGeometry, QgsFillSymbol


from PyQt5.QtGui import QColor
from qgis.core import QgsTextFormat, QgsTextBufferSettings, QgsTextBackgroundSettings
from qgis.core import QgsTextRenderer, QgsLayoutUtils, QgsTextFragment, QgsTextDocument, QgsTextBlock
from qgis.core import QgsPalLayerSettings, QgsVectorLayerSimpleLabeling


# Добавим новую функцию для получения кадастрового номера по GPS-координатам
def get_cadastre_number_from_coordinates(latitude, longitude):
    url = f"https://pkk.rosreestr.ru/api/features/1?text={latitude},{longitude}&limit=1&tolerance=1"
    response = requests.get(url, verify=False).json()
    
    features = response.get("features", [])
    if features:
        return features[0]["attrs"]["cn"]
    
    return None
    



def get_mercator_to_gps(x ,y):
        # Преобразование координат в EPSG:4326
        source_crs = QgsCoordinateReferenceSystem('EPSG:3857')
        dest_crs = QgsCoordinateReferenceSystem('EPSG:4326')
        transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())
        pt = transform.transform(QgsPointXY(x, y))
        return pt.x(), pt.y()

def get_coordinates_from_feature(feature):
    center = feature['center']

    if isinstance(center, dict):
        x, y = float(center['x']), float(center['y'])
        return get_mercator_to_gps(x ,y)

    return None

def get_category_name(code):
    CATEGORY_TYPES = {
        "003001000000": "Земли сельскохозяйственного назначения",
        "003002000000": "Земли поселений (земли населенных пунктов)",
        "003003000000": "Земли промышленности, энергетики, транспорта, связи, радиовещания, телевидения, информатики, земли для обеспечения космической деятельности, земли обороны, безопасности и земли иного специального назначения",
        "003004000000": "Земли особо охраняемых территорий и объектов",
        "003005000000": "Земли лесного фонда",
        "003006000000": "Земли водного фонда",
        "003007000000": "Земли запаса",
        "003008000000": "Категория не установлена"
    }
    return CATEGORY_TYPES.get(code, "Неизвестная категория")


# получение текста ЗОУИТ если есть для gps-координаты
def get_zouit_value(latitude, longitude):
    #url = f"https://pkk.rosreestr.ru/api/features/10?text={latitude},{longitude}&tolerance=1"
    url = f"https://pkk.rosreestr.ru/api/features/?text={latitude}+{longitude}&tolerance=1&types=[10,20]"
    response = requests.get(url, verify=False).json()
    
    features = response.get("results", [])
    if not features:
       return None

    result = "<ul>"
    for feature in features:
       number_zone = feature["attrs"]["number_zone"]
       zone_type = feature["type"]
       url = f"https://pkk.rosreestr.ru/api/features/{zone_type}/{number_zone}"
       response = requests.get(url, verify=False).json()
       result += "<li>" + number_zone + ": " + response['feature']['attrs']['name_zone'] + "</li>"

    return result + "</ul>"

# x,y - координаты объекта, cx, cy - координаты клика
def create_geojson_file(cnum, q, x, y, cx, cy):
    geojson_filename = os.path.abspath(__file__) + 'pkk6.geojson'

    address = str(q['feature']['attrs']['address'])[:254]
    util_by_doc = str(q['feature']['attrs']['util_by_doc'])[:254]
    area_value = q['feature']['attrs']['area_value'] / 100.0
    pkk_url = f"https://pkk.rosreestr.ru/#/search/{y},{x}/18/@5w3tqw5cp"
    zouit_url = f"https://pkk.rosreestr.ru/#/search/{y},{x}/17/@3zpf1bvh5"
    cad_cost = q['feature']['attrs']['cad_cost']
    date_cost = q['feature']['attrs']['date_cost']
    category_type = get_category_name(q['feature']['attrs']['category_type'])

    zouit_value = get_zouit_value(cx, cy)

    print(f"Адрес: {address}\nПлощадь: {area_value} сот.\nКатегория: {category_type}\nРазеш: {util_by_doc}\nПКК:\n{pkk_url}\nЗОУИТ:\n{zouit_url}\nКад.цена: { '{:0,.2f}'.format(cad_cost) } руб.({date_cost})\n{zouit_value}")


    util_mapping = {
        "для индивидуального жилищного строительства": "ИЖС",
        "под индивидуальное жилищное строительство": "ИЖС",
        "для сельскохозяйственного производства": "С/Х",
    }
    util_by_doc_lower = util_by_doc.lower()
    util_by_doc = util_mapping.get(util_by_doc_lower, util_by_doc)

    geojson_data = {
      "type": "FeatureCollection",
      "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [x, y]
            },
            "properties": {
                "cnum": cnum,
                "address": address,
                "util_by_doc": util_by_doc,
                "area_value": area_value,
                "gps": [y, x],
                "pkk_url": pkk_url,
                "cad_cost": cad_cost,
                "category_type": category_type,
                "description": f"Площадь: {area_value} сот.%{category_type}%{util_by_doc}%{cnum}%Кад.цена: {'{:0,.2f}'.format(cad_cost)} руб.({date_cost})"
            }
        }
      ]
    }

    # Добавляем вторую фичу только при наличии zouit_value
    if zouit_value:
      geojson_data["features"].append({
          "type": "Feature",
          "geometry": {
              "type": "Point",
              "coordinates": [cy, cx]
          },
          "properties": {
              "description": zouit_value
          }
      })

    with open(geojson_filename, 'w') as geojson_file:
        geojson_file.write(json.dumps(geojson_data))

    return geojson_filename


def create_geojson_file_zouit_only(cx, cy):
    geojson_filename = os.path.abspath(__file__) + 'pkk6.geojson'

    zouit_value = get_zouit_value(cx, cy)
    geojson_data = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [cy, cx]
        },
        "properties": {
            "gps": [cx,cy],
            "description": f"{zouit_value if zouit_value else 'нет данных'}"
        }
    }
    with open(geojson_filename, 'w') as geojson_file:
        geojson_file.write(json.dumps(geojson_data))
    return geojson_filename


def add_geojson_layer_to_project(cnum, geojson_filename):
    geojson_layer = QgsVectorLayer(geojson_filename, f'pkk6_geojson_{cnum}', 'ogr')

    # Создаем стиль маркера
    symbol = QgsMarkerSymbol.createSimple({'name': 'square', 'color': 'red'})

    # Устанавливаем стиль маркера для слоя
    symbol_layer = QgsSimpleMarkerSymbolLayer.create({'name': 'star', 'color': 'red', 'size': 7})

    symbol.changeSymbolLayer(0, symbol_layer)

    # Создаем рендерер с установленным символом
    renderer = geojson_layer.renderer()
    renderer.setSymbol(symbol)



    label_settings = QgsPalLayerSettings()
    label_settings.drawLabels = True
    label_settings.fieldName = 'description'
    label_settings.placement = QgsPalLayerSettings.AroundPoint
    label_settings.wrapChar = "%"
    label_settings.autoWrapLength = 100
    label_settings.yOffset = 10
    label_settings.scaleVisibility = True
    label_settings.maximumScale = 2
    label_settings.maximumScale = 0

    text_format = QgsTextFormat()
    background_settings = QgsTextBackgroundSettings()
    background_settings.setEnabled(True)
    background_settings.setOpacity(0.5)  # Установите значение прозрачности (от 0.0 до 1.0)

    text_format.setAllowHtmlFormatting(True)
    text_format.setBackground(background_settings)
    label_settings.setFormat(text_format)


    geojson_layer.setLabelsEnabled(True)
    geojson_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))


    # Добавляем слой в проект
    QgsProject.instance().addMapLayer(geojson_layer)


def centrate(latitude, longitude):
    # Создаем объект QgsPointXY с координатами
    gps_point = QgsPointXY(longitude, latitude)

    # Преобразуем координаты в EPSG:4326
    source_crs = QgsCoordinateReferenceSystem('EPSG:4326')
    dest_crs = QgsCoordinateReferenceSystem('EPSG:3857')  # Пример - используйте тот, который вам нужен
    transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())
    transformed_point = transform.transform(gps_point)

    # Устанавливаем центр карты
    iface.mapCanvas().setCenter(transformed_point)

    # Обновляем карту
    iface.mapCanvas().refresh()



def pkk6_search(cnum, pkklink, cnumid, q, cx, cy):
    x, y = None, None

    if not cnum:
        x, y = cx, cy
        geojson_filename = create_geojson_file_zouit_only(cx, cy)        
        add_geojson_layer_to_project(None, geojson_filename)

    elif isinstance(q['feature'], type(None)):
        QMessageBox.information(iface.mainWindow(),
                                cnum,
                                'Ошибка ввода или объект отсутствует в ПКК')
    else:
        coordinates = get_coordinates_from_feature(q['feature'])

        if coordinates:
            x, y = coordinates
            geojson_filename = create_geojson_file(cnum, q, x, y, cx, cy)
            add_raster_layer_to_project(cnum, pkklink, cnumid, q)  # Добавляем растровый слой
            add_geojson_layer_to_project(cnum, geojson_filename)

        else:
            QMessageBox.information(iface.mainWindow(),
                                    cnum,
                                    'Без координат границ или что-то пошло не так')
    return x, y


class Pkk6Search:
    def __init__(self, iface):
        self.iface = iface
        self.tool = None
        self.action = None

    def initGui(self):
        # курсор-плагин
        # Создаем кнопку в панели инструментов
        self.toolButton = QAction("Курсор", self.iface.mainWindow())
        self.toolButton.triggered.connect(self.runCursor)
        self.iface.addToolBarIcon(self.toolButton) #

        # основной плагин
        self.action = (QAction(QIcon(os.path.dirname(__file__) + "/icon.png"),
            'Поиск по Публичной кадастровой карте',
            self.iface.mainWindow()))
        self.action.triggered.connect(self.runPopup)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action
        # Удаляем кнопку из панели инструментов и отключаем действие
        self.toolButton.triggered.disconnect(self.runCursor)
        self.iface.removeToolBarIcon(self.toolButton)
        del self.toolButton
        clear_layers()


    def runCursor(self):
        # логика плагина Курсор
        if self.tool is None:
            self.tool = MapClickTool(self.iface.mapCanvas())
            self.iface.mapCanvas().setMapTool(self.tool)
        else:
            self.iface.mapCanvas().unsetMapTool(self.tool)
            del self.tool
            self.tool = None
            clear_layers()            





    def runPopup(self):
        input, ok = QInputDialog.getText(QInputDialog(),
            "Найти на Публичной кадастровой карте",
            "Введите кадастровый номер ЗУ, ОКС или GPS-координаты (через запятую)")
            
        if ok:
            doForString(input, True)


def clear_layers():
    for layer in QgsProject.instance().mapLayers().values():
        if layer.name().startswith('pkk6_geojson'):
            QgsProject.instance().removeMapLayers([layer.id()])
        elif layer.name().startswith('pkk6_raster'):
            QgsProject.instance().removeMapLayers([layer.id()])
    iface.mapCanvas().refresh()


def doForString(input, needCenter):
            cx, cy = None, None

            if not input:
                return

            if ',' in input:
                # Если введены GPS-координаты
                try:
                    cx, cy = map(float, input.split(','))
                    cadastre_number = get_cadastre_number_from_coordinates(cx, cy)
                    if cadastre_number:
                        input = cadastre_number
                    else:
                    #    QMessageBox.information(iface.mainWindow(),
                    #                            "Ошибка",
                    #                            "Не удалось получить кадастровый номер по указанным координатам.")
                        pkk6_search(None, None, None, None, cx, cy)
                        return
                except ValueError:
                    QMessageBox.information(iface.mainWindow(),
                                            "Ошибка",
                                            "Некорректный формат GPS-координат.")
                    return

            loop = True
            cou = 0
            while loop and cou < 60:
                try:                                           
                        clear_layers()

                        cnum = str(input.strip())

                        cnumid = re.sub(':0{1,6}', ':', (str(input.strip()).lstrip('0'))).replace('::', ':0:') 

                        if (len(str((requests.get('https://pkk.rosreestr.ru/api/features/1/' + str(cnumid), verify=False).json()['feature'])))) > 20:
                            pkklink = ('https://pkk.rosreestr.ru/api/features/1/' + cnumid)
                            q = requests.get(pkklink, verify=False).json()               
                            x,y = pkk6_search(cnum, pkklink, cnumid, q, cx, cy)
                        elif isinstance(requests.get('https://pkk.rosreestr.ru/api/features/1/' + str(cnumid), verify=False).json()['feature'], type(None)):
                            pkklink = ('https://pkk.rosreestr.ru/api/features/5/' + cnumid)
                            q = requests.get(pkklink, verify=False).json()
                            x,y = pkk6_search(cnum, pkklink, cnumid, q, cx, cy)
                        loop = False
            
                        # Установим видимость карты вокруг центральной точки объекта
                        if needCenter:
                           centrate(y, x)


                except requests.exceptions.SSLError:
                    cou += 1
                    loop = True
                except requests.exceptions.ConnectionError:
                    cou += 1
                    loop = True
                if cou == 60:
                    QMessageBox.information(iface.mainWindow(),
                    str(cou),
                    'Превышено количество запросов.')

# Добавляем новый метод для создания и добавления растрового слоя
def add_raster_layer_to_project(cnum, pkklink, cnumid, q):
        xmin = (((q['feature']))['extent']['xmin'])      
        ymin = (((q['feature']))['extent']['ymin'])
        xmax = (((q['feature']))['extent']['xmax'])
        ymax = (((q['feature']))['extent']['ymax'])

        img_size_x = round(float(xmax) - float(xmin))
        img_size_y = round(float(ymax) - float(ymin))

        imgURL = ''   

        if '/1/' in pkklink:
            imgURL = 'https://pkk.rosreestr.ru/arcgis/rest/services/PKK6/CadastreSelected/MapServer/export?bbox={}%2C{}%2C{}%2C{}&bboxSR=102100&imageSR=102100&size={}%2C{}&dpi=96&format=png32&transparent=true&layers=show%3A6%2C7%2C8%2C9&layerDefs=%7B%226%22%3A%22ID%20=%20%27{}%27%22%2C%227%22%3A%22ID%20=%20%27{}%27%22%2C%228%22%3A%22ID%20=%20%27{}%27%22%2C%229%22%3A%22ID%20=%20%27{}%27%22%7D&f=image'.format(xmin, ymin, xmax, ymax, img_size_x, img_size_y, cnumid, cnumid, cnumid, cnumid)
        elif '/5/' in pkklink:
            imgURL = 'https://pkk.rosreestr.ru/arcgis/rest/services/PKK6/CadastreSelected/MapServer/export?bbox={}%2C{}%2C{}%2C{}&bboxSR=102100&imageSR=102100&size={}%2C{}&dpi=96&format=png32&transparent=true&layers=show%3A0%2C1%2C2%2C3%2C4%2C5&layerDefs=%7B%220%22%3A%22ID%20%3D%20%27{}%27%22%2C%221%22%3A%22ID%20%3D%20%27{}%27%22%2C%222%22%3A%22ID%20%3D%20%27{}%27%22%2C%223%22%3A%22ID%20%3D%20%27{}%27%22%2C%224%22%3A%22ID%20%3D%20%27{}%27%22%2C%225%22%3A%22ID%20%3D%20%27{}%27%22%7D&f=image'.format(xmin, ymin, xmax, ymax, img_size_x, img_size_y, cnumid, cnumid, cnumid, cnumid, cnumid, cnumid)

        #if os.path.exists(os.path.abspath(__file__) + 'pkk6.png'):
        #    os.remove(os.path.abspath(__file__) + 'pkk6.png')

        loop = True
        cou = 0
        while loop and cou < 60:       
            try:
                ssl._create_default_https_context = ssl._create_unverified_context
                urllib.request.urlretrieve(imgURL, os.path.abspath(__file__) + 'pkk6.png')
                if os.path.exists(os.path.abspath(__file__) + 'pkk6.png'):       
                    rast = gdal.Open(os.path.abspath(__file__) + 'pkk6.png')               
                    with open (os.path.abspath(__file__) + 'pkk6.pgw', 'w') as target:
                        pxs = str((float(xmax) - float(xmin)) / int(rast.RasterXSize))   
                        xminpng = str(xmin + float(pxs) / 2)  
                        ymaxpng = str(ymax - float(pxs) / 2)
                        target.write(pxs + '\n' + '0\n0\n' + '-' + pxs + '\n'+ xminpng + '\n' + ymaxpng)                   
                    rastlr = iface.addRasterLayer(os.path.abspath(__file__) + 'pkk6.png', 'pkk6_raster_' + cnum)
                    rastlr.setCrs(QgsCoordinateReferenceSystem('EPSG:3857'))              
                    if '/1/' in pkklink:
                        rastlr.renderer().setOpacity(0.5)
                    elif '/5/' in pkklink:
                        rastlr.renderer().setOpacity(0.5)
                        rastlr.renderer().setRedBand(1)
                        rastlr.renderer().setBlueBand(0)
                        rastlr.renderer().setGreenBand(0)
                    loop = False
            except Exception as e:
                print(e)
                cou += 1
                loop = True
            if cou == 60:
                QMessageBox.information(iface.mainWindow(),
                                        cnum,
                                        'Превышено количество запросов')
                
        iface.mapCanvas().refresh()



######################################
##
## КУРСОР
##
######################################
class MapClickTool(QgsMapTool):
    def __init__(self, canvas):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas

    def canvasPressEvent(self, event):

        clear_layers()
        
        if event.button() == 2:
            return

        point = self.toMapCoordinates(event.pos())
        cx, cy = get_mercator_to_gps(point.x(), point.y())        

        app = QApplication.instance()
        if app is None:
          app = QApplication([])

        # Устанавливаем курсор ожидания
        app.setOverrideCursor(Qt.WaitCursor)        
        try:

          #cadastre_number = get_cadastre_number_from_coordinates(cy, cx)
          #print(f'Кадастровый номер: {cadastre_number}')
          doForString(f"{cy},{cx}", False)
      
        finally:
          # Восстанавливаем курсор в его стандартное состояние
          app.restoreOverrideCursor()


