from qgis.PyQt.QtWidgets import QAction, QLineEdit, QPushButton, QWidget, QVBoxLayout, QHBoxLayout
from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsPointXY, QgsGeometry, QgsCoordinateTransform
from qgis.gui import QgsMapTool, QgsMapToolEmitPoint
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QMessageBox


import requests, os

class GeoCoderPlugin:
    def __init__(self, iface):
        self.plugin_dir = os.path.dirname(__file__)
        self.iface = iface
        self.input_box = None
        self.search_button = None
        self.canvas = self.iface.mapCanvas()
        self.setup_ui()

    def initGui(self):
        pass

    def unload(self):
        pass

    def setup_ui(self):
        container = QWidget()
        layout = QHBoxLayout()

        self.input_box = QLineEdit()
        self.search_button = QPushButton()
        icon_path = self.plugin_dir + '/icons/mActionZoom.png'
        self.search_button.setIcon(QIcon(icon_path))  # Путь к значку лупы

        self.search_button.setIconSize(self.search_button.sizeHint()*0.7)  # Уменьшаем размер значка        
        self.search_button.clicked.connect(self.search_location)

        layout.addWidget(self.input_box)
        layout.addWidget(self.search_button)
        
        container.setLayout(layout)
        
        self.iface.addToolBarWidget(container)
        self.input_box.returnPressed.connect(self.search_location)


    def search_location(self):
        location = self.input_box.text()
        if location:
            coordinates = self.geocode(location)
            if coordinates:
                self.center_map(coordinates)
            else:
                print('failed')
                QMessageBox.warning(None, 'GeoCoder Plugin', 'Объект не найден!')

    def geocode(self, location):
        api_key = 'c35910a6-13b9-4a5e-bd77-f45b5dfd843b'
        url = f'https://geocode-maps.yandex.ru/1.x/?apikey={api_key}&format=json&geocode={location}'

        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'response' in data and 'GeoObjectCollection' in data['response']:
                features = data['response']['GeoObjectCollection']['featureMember']
                if features:
                    coords_str = features[0]['GeoObject']['Point']['pos']
                    coords = list(map(float, coords_str.split()))
                    return QgsPointXY(coords[0], coords[1])
        return None

    def center_map(self, point):
        crs_source = QgsCoordinateReferenceSystem(4326)  # WGS 84
        crs_dest = self.canvas.mapSettings().destinationCrs()

        transform = QgsCoordinateTransform(crs_source, crs_dest, QgsProject.instance())
        
        point_transformed = transform.transform(point)
        
        self.canvas.setCenter(point_transformed)
        self.canvas.refresh()

def classFactory(iface):
    return GeoCoderPlugin(iface)
