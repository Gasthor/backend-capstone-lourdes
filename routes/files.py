from flask import Blueprint, abort, json, request, jsonify, send_file
from datetime import datetime
import os
import pandas as pd

from logic.files import search_file

files_bp = Blueprint('files', __name__)

@files_bp.route('/upload', methods=['POST'])
def upload_excel():
    data = request.form.get("data")
    color = request.form.get("COLOR VARIEDAD")

    data_dict = json.loads(data)

    print(data, color)
    # Invertir clave-valor ejemplo: {"hola" : "chao"} => {"chao" : "hola"}
    #data_dict_upper = {k.upper(): v.upper() for k, v in data_dict.items()}

    data = {v: k for k, v in data_dict.items()}
    print(data, color)

    jsonify(data)

    if 'file' not in request.files:
        return jsonify({"error": "No se cargo el archivo1"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "Archivo sin nombre"}), 400

    if file and file.filename.endswith('.xlsx'):
        
        try:
            df = pd.read_excel(file)
            #df = df.apply(lambda x: x.str.upper() if x.dtype == "object" else x)
            df = df.rename(columns= data, errors="raise")
            date = df["FECHA"].iloc[0]

            if int(date):
                df["FECHA"] = pd.to_numeric(df["FECHA"], errors="coerce")
                df["FECHA"] = pd.to_datetime(df["FECHA"], unit="D", origin="1899-12-30")
                df["FECHA"] = df["FECHA"].dt.date

            df["FECHA"] = pd.to_datetime(df["FECHA"])
            df["DIA"] = df["FECHA"].dt.day
            df["MES"] = df["FECHA"].dt.month
            df["AÑO"] = df["FECHA"].dt.year
            year = df["AÑO"].iloc[0]
            name_file = f"Vendimia_{year}.xlsx"
            check_file = search_file("./uploads",f"Vendimia_{year}.xlsx")
            if check_file  == name_file:
                return jsonify({"error": f"El año de vendimia {year} ya se encuentra cargado, por favor elimine el archivo antes de subir uno nuevo del mismo año"}), 400
            
            else:
                #### LOGICA ETL Y AGREGAR DF AL HISTORICO

                if color != None:
                    df = df.rename(columns={color: "COLOR VARIEDAD"})
                    df = df[df["COLOR VARIEDAD"] == "T"]
                    df = df.drop("COLOR VARIEDAD", axis=1)
                else:
                    df = df[(df["FAMILIA"] != "Viognier") & df["FAMILIA"] != "Chardonnay" & df["FAMILIA"] != "Gewurztraminer" & df["FAMILIA"] != "Riesling" & df["FAMILIA"] != "Sauvignon Blanc" & df["FAMILIA"] != "Semillon"]

                df["CALIDAD"] = df["CALIDAD"].replace({'BL': 'Blend', 'PR': 'Premium'})
                df["FAMILIA"] = df["FAMILIA"].str.upper()
                df["PRODUCTOR"] = df["PRODUCTOR"].str.upper()
                df["RUT"] = df["RUT"].astype(str)

                df["NUM_SEMANA"] = df["FECHA"].dt.strftime("%G-%V")
                df["NUM_SEMANA"] = df.groupby(df["FECHA"].dt.year)["NUM_SEMANA"].transform(lambda x: (pd.to_numeric(x.str[-2:]) - pd.to_numeric(x.str[-2:]).min() + 1))


                #######
                df = df[["FECHA", "CONTRATO", "PRODUCTOR", "KILOS ENTREGADOS", "RUT", "FAMILIA", "AREA", "CALIDAD", "NUM_SEMANA", "DIA", "MES", "AÑO"]]
                
                

                ###Agregar informacion a archivo historico de vendimias
                if search_file("./generated_excel/", "Vendimia_historica.xlsx") == "Archivo no encontrado.":
                    filepath = os.path.join("./generated_excel/","Vendimia_historica.xlsx")
                    os.makedirs("./generated_excel/", exist_ok=True)
                    df.to_excel(filepath,index=False)
                else:
                    df_historico = pd.read_excel("./generated_excel/Vendimia_historica.xlsx")
                    result = df_historico[df_historico["AÑO"] == year]
                    if len(result) > 0:
                        df_historico = df_historico[df_historico["AÑO"] != year]
                    df_historico = pd.concat([df_historico, df])

                    df_historico = df_historico.sort_values(by="FECHA")

                    filepath = os.path.join("./generated_excel/","Vendimia_historica.xlsx")
                    os.makedirs("./generated_excel/", exist_ok=True)
                    df_historico.to_excel(filepath,index=False)
                
                

                ###Guardar archivo en carpeta uploads
                filepath = os.path.join("./uploads/",name_file)
                os.makedirs("./uploads/", exist_ok=True)
                df.to_excel(filepath,index=False)

                return jsonify({"message": f"Archivo de la vendimia {year} cargado con exito"}), 200
 
        except Exception as e:
            return jsonify({"error": "Nombre especificado para la columna: " + str(e) + " no coincide con una columna del archivo cargado"}), 500
    else:
        return jsonify({"error": "Archivo cargado no es .xlsx"}), 400
    
@files_bp.route('/delete/<name>', methods=['DELETE'])
def delete_excel(name):
    try:
        os.remove(f"./uploads/{name}.xlsx")
        ### LOGICA DE ELIMINAR ARCHIVO DE DF HISTORICO
    except :
            return jsonify({"error": "Archivo no encontrado, si el problema persiste, comunicarse con el administrador."}), 500 
    return jsonify({"message": f"Archivo '{name}' eliminado con exito"}), 200

@files_bp.route('/', methods=['GET'])
def get_files():
    folder = os.listdir("./uploads")
    files = [name for name in folder if os.path.isfile(os.path.join("./uploads",name))]
    response = []
    for file in files:
        file = file.replace("_",".")
        file = file.split(".")
        response.append({ "name" : file[0], "year" : file[1]})
    
    response = sorted(response, key=lambda x: x["year"])

    return response, 200

@files_bp.route('/download/<path:filename>', methods=['GET'])
def download(filename):
    print(filename)
    try:
        file_path = f"./generated_excel/{filename}"
        if search_file("./generated_excel/", "Vendimia_historica.xlsx") == "Archivo no encontrado.":
            abort(404, description="File not found")
        # Crear una respuesta HTTP con el archivo adjunto
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        print(f"Error al procesar la solicitud: {e}")
        abort(500, description="Internal server error")


