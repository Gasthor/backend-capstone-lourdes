from flask import Blueprint, request, jsonify
from datetime import datetime
import os
import pandas as pd

from logic.files import rename_column, search_file

files_bp = Blueprint('files', __name__)

@files_bp.route('/upload', methods=['POST'])
def upload_excel():
    data = request.form
    data = data.to_dict()
    jsonify(data)
    data = {v: k for k, v in data.items()}

    if 'file' not in request.files:
        return jsonify({"error": "No se cargo el archivo1"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "Archivo sin nombre"}), 400

    if file and file.filename.endswith('.xlsx'):
        
        try:
            df = pd.read_excel(file)
            df = df.rename(columns= data)
            date = df["FECHA"].iloc[0]

            if int(date):
                df["FECHA"] = pd.to_numeric(df["FECHA"], errors="coerce")
                df["FECHA"] = pd.to_datetime(df["FECHA"], unit="D", origin="1899-12-30")
                df["FECHA"] = df["FECHA"].dt.date

            df["FECHA"] = pd.to_datetime(df["FECHA"])
            df["AÑO"] = df["FECHA"].dt.year
            year = df["AÑO"].iloc[0]
            name_file = f"Vendimia_{year}.xlsx"
            check_file = search_file("./uploads",f"Vendimia_{year}.xlsx")
            if check_file  == name_file:
                return jsonify({"error": f"El año de vendimia {year} ya se encuentra cargado, por favor elimine el archivo antes de subir uno nuevo del mismo año"}), 400
            
            else:
                filepath = os.path.join("./uploads/",name_file)
                os.makedirs("./uploads/", exist_ok=True)
                df.to_excel(filepath,index=False)
                return jsonify({"message": f"Archivo de la vendimia {year} cargado con exito"}), 200
 
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Archivo cargado no es .xlsx"}), 400