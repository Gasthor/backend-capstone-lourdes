from flask import Blueprint, abort, json, request, jsonify, send_file
from datetime import datetime
import os
import pandas as pd

from logic.files import search_file

files_bp = Blueprint('files', __name__)

# Ruta para subir archivos referente a las vendimias
@files_bp.route('/upload', methods=['POST'])
def upload_excel():
    data = request.form.get("data")
    color = request.form.get("COLOR VARIEDAD")

    data_dict = json.loads(data)

    data = {v: k for k, v in data_dict.items()}

    jsonify(data)

    if 'file' not in request.files:
        return jsonify({"error": "No se cargo el archivo"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "Archivo sin nombre"}), 400

    if file and file.filename.endswith('.xlsx'):
        
        try:
            df = pd.read_excel(file)

            df = df.rename(columns= data, errors="raise")

            if pd.api.types.is_numeric_dtype(df["FECHA"]):
                df["FECHA"] = pd.to_datetime(df["FECHA"], unit='D', origin='1899-12-30', errors='coerce')
            else:
                df["FECHA"] = pd.to_datetime(df["FECHA"], errors='coerce')

            df = df.dropna(subset=['FECHA'])

            df["DIA"] = df["FECHA"].dt.day
            df["MES"] = df["FECHA"].dt.month
            df["AÑO"] = df["FECHA"].dt.year.astype(int)
            year = df["AÑO"].iloc[0]
            
            name_file = f"Vendimia_{year}.xlsx"
            check_file = search_file("./uploads",f"Vendimia_{year}.xlsx")
            if check_file  == name_file:
                return jsonify({"error": f"El año de vendimia {year} ya se encuentra cargado, por favor elimine el archivo antes de subir uno nuevo del mismo año"}), 400
            
            else:

                if color and color != "":
                    df = df.rename(columns={color: "COLOR VARIEDAD"})
                    df = df[df["COLOR VARIEDAD"] == "T"]
                    df = df.drop("COLOR VARIEDAD", axis=1)
                else:
                    df = df[(df["FAMILIA"] != "Viognier") & (df["FAMILIA"] != "Chardonnay") & (df["FAMILIA"] != "Gewurztraminer") & (df["FAMILIA"] != "Riesling") & (df["FAMILIA"] != "Sauvignon Blanc") & (df["FAMILIA"] != "Semillon")]

                df["CALIDAD"] = df["CALIDAD"].replace({'BL': 'Blend', 'PR': 'Premium'})
                df["FAMILIA"] = df["FAMILIA"].str.upper()
                df["PRODUCTOR"] = df["PRODUCTOR"].str.upper()
                df["RUT"] = df["RUT"].astype(str)

                df["NUM_SEMANA"] = df["FECHA"].dt.strftime("%G-%V")
                df["NUM_SEMANA"] = df.groupby(df["FECHA"].dt.year)["NUM_SEMANA"].transform(lambda x: (pd.to_numeric(x.str[-2:]) - pd.to_numeric(x.str[-2:]).min() + 1))

                df = df[["FECHA", "CONTRATO", "PRODUCTOR", "KILOS ENTREGADOS", "RUT", "FAMILIA", "AREA","GRADO BRIX","TEMPERATURA", "CALIDAD", "NUM_SEMANA", "DIA", "MES", "AÑO"]]

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
    
# Ruta para eliminar una vendimia del sistema
@files_bp.route('/delete/<name>/<year>', methods=['DELETE'])
def delete_excel(name,year):
    try:
        os.remove(f"./uploads/{name}_{year}.xlsx")
        
        df_historico_delete = pd.read_excel("./generated_excel/Vendimia_historica.xlsx")
        df_historico_delete = df_historico_delete[df_historico_delete["AÑO"] != int(year)]

        filepath = os.path.join("./generated_excel/","Vendimia_historica.xlsx")
        os.makedirs("./generated_excel/", exist_ok=True)
        df_historico_delete.to_excel(filepath,index=False)

    except :
            return jsonify({"error": "Archivo no encontrado, si el problema persiste, comunicarse con el administrador."}), 500 
    return jsonify({"message": f"Archivo '{name}' eliminado con exito"}), 200

#Ruta para obtener los archivos cargados en el sistema
@files_bp.route('/', methods=['GET'])
def get_files():
    folder = os.listdir("./uploads")
    files = [name for name in folder if os.path.isfile(os.path.join("./uploads",name))]
    if len(files) == 0:
        return jsonify({"message" : "No hay vendimias cargadas en el sistema."})
    df= pd.read_excel("./generated_excel/Vendimia_historica.xlsx")

    response = []
    for file in files:
        file = file.replace("_",".")
        file = file.split(".")
        ## Obtener los kilos producidos por semana en el año iterado
        year = int(file[1])

        df_filtred = df[df["AÑO"] == year]
        df_grouped = df_filtred.groupby(["NUM_SEMANA"])["KILOS ENTREGADOS"].sum().reset_index()
        df_grouped = df_grouped.rename(columns={"NUM_SEMANA":"Semana", "KILOS ENTREGADOS": "Kilos"})
        df_json = df_grouped.to_dict(orient="records")

        print(df_json)

        response.append({ "name" : file[0], "year" : file[1], "data": df_json})



    
    response = sorted(response, key=lambda x: x["year"])

    return response, 200

#Ruta para descargar archivo historico de vendimias cargadas en el sistema
@files_bp.route('/download/<path:filename>', methods=['GET'])
def download(filename):
    try:
        file_path = f"./generated_excel/{filename}"
        if search_file("./generated_excel/", "Vendimia_historica.xlsx") == "Archivo no encontrado.":
            abort(404, description="File not found")
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        print(f"Error al procesar la solicitud: {e}")
        abort(500, description="Internal server error")


