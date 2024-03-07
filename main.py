from flask import Flask, request, jsonify
from google.auth import compute_engine
from time import sleep
from ee_utils import *
import geemap
import ee

app = Flask(__name__)
app.config.from_pyfile('settings.py')

@app.before_request
def before():
    service_account = "lst-backend@ee-stellarisoft-ou-lst.iam.gserviceaccount.com"
    credentials = ee.ServiceAccountCredentials(service_account, './ee-stellarisoft-ou-lst-67b84b09a68c.json')
    ee.Initialize(credentials)

@app.route("/")
def home():
    return "Home"

@app.route("/get-img")
def get_user():

    roi = ee.Geometry.Point(-110.97732, 29.1026)
    collection = (
        ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        .filterDate('2024-01-01', '2024-12-31')
        .filterBounds(roi)
        .filterMetadata('CLOUD_COVER', 'less_than', 10)
        .sort("DATE_ACQUIRED", False)
    )

    area = ee.Geometry.BBox(-111.14, 28.93, -110.82, 29.28)
    image = collection.first().clip(area)

    STB10 = image.select("ST_B10")
    ST = STB10.expression(' M * STB10 + A - 273.15', {
        'M': image.get("TEMPERATURE_MULT_BAND_ST_B10").getInfo(),
        'STB10': STB10,
        'A': image.get("TEMPERATURE_ADD_BAND_ST_B10").getInfo()
    })

    STstats = geemap.image_stats(ST).getInfo()

    STcontours = geemap.create_contours(ST, 40, 66, 1, region=area)

    fecha = image.get('DATE_ACQUIRED').getInfo()

    projection = STB10.projection().getInfo()
    
    task = ee.batch.Export.image.toDrive(
        image =  ST,
        description = 'hmo_{}_lst'.format(fecha),
        folder = 'HMO_LST',
        fileNamePrefix = 'hmo_{}_lst'.format(fecha),
        region = area,
        fileFormat = 'GeoTIFF'
    )
    task.start()

    status = ''

    '''
    while status != 'COMPLETED':
        sleep(1)
        print(task.status()['id'])
        print(task.status()['state'])
        if task.status()['id'] == 'COMPLETED':
            break
    '''

    url = image_to_map_id(ST)

    data = {
        "no_of_imgs": collection.size().getInfo(),
        "images": collection.aggregate_array('system:id').getInfo(),
        "STstats": STstats,
        "fecha": fecha,
        "url": url
    }



    return jsonify(data), 200


    

    

@app.route("/create-user", methods=["POST"])
def create_user():
    data = request.get_json()

    return jsonify(data), 201

if __name__ == "__main__":
    app.run(debug=True)
