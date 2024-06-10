from flask import Blueprint, json, jsonify, request
import numpy as np
import pandas as pd

from logic.algoritmo import generar_semanas, pesos_semanal
from logic.files import search_file

vendimia_bp = Blueprint('vendimia', __name__)

@vendimia_bp.route('/', methods=['POST'])
def get_files():
    data = request.form.get("years")
    if not data:
        return jsonify({"error": "No se proporcionaron años"}), 400

    if search_file("./generated_excel/", "Vendimia_historica.xlsx") == "Archivo no encontrado.":
        return jsonify({"error": "No hay vendimias historicas disponibles"}), 404

    df = pd.read_excel("./generated_excel/Vendimia_historica.xlsx")

    try:
        years = json.loads(data)
    except json.JSONDecodeError:
        return jsonify({"error": "Formato de datos incorrecto"}), 400

    if not isinstance(years, list):
        return jsonify({"error": "Formato de datos incorrecto"}), 400

    df_select = df[df['AÑO'].isin(years)] 

    df_grouped = df_select.groupby(["NUM_SEMANA","AÑO"])["KILOS ENTREGADOS"].sum().reset_index()
    df_grouped = df_grouped.rename(columns={"NUM_SEMANA":"Semana", "KILOS ENTREGADOS": "Kilos"})
    df_resumen = df_grouped.groupby(["Semana"])["Kilos"].mean().reset_index()
    df_json = df_resumen.to_dict(orient="records")

    min_week = df_grouped['Semana'].min()
    max_week = df_grouped['Semana'].max()
    duration_weeks = int(max_week - min_week + 1)
    weeks = []
    for i in range(duration_weeks):
        week = []
        if i == 0:
            week.append(1)
            week.append("1 Semana")
        else:
            week.append(i+1)
            week.append(str(i+1) + " Semanas")
        weeks.append(week)

    formatted_years = ', '.join(map(str, years))
    total_kilos = int(df_resumen['Kilos'].sum())

    return jsonify({
        "data": df_json,
        "years": formatted_years,
        "total": total_kilos,
        "duration": duration_weeks,
        "weeks": weeks
    }), 200

@vendimia_bp.route('/planificacion', methods=['POST'])
def strat_planning():
    try:
        years_selected = request.form.get("years")
        obj_kilos = request.form.get("obj_kilos")
        limit_week = request.form.get("limit_week")
        factor_week = request.form.get("factor_week")
        duration = int(request.form.get("duration"))
    except Exception as e:
        return jsonify({
        "error": f"Error al enviar datos: {e}"
        }), 400
    
    try:
        years_selected = json.loads(years_selected)
        limit_week = json.loads(limit_week)
        factor_week =  json.loads(factor_week)
    except json.JSONDecodeError:
        return jsonify({"error": "Formato de datos incorrecto"}), 400

    if search_file("./generated_excel/", "Vendimia_historica.xlsx") == "Archivo no encontrado.":
        return jsonify({"error": "No hay vendimias historicas disponibles"}), 404
    

    limit_week = {int(k): v for k, v in limit_week.items()}
    factor_week = {int(k): v for k, v in factor_week.items()}

    list_limit_week = []
    list_factor_week = []

    for i in range(duration):
        value = limit_week.get(i, 0)
        if value != 0:
            value = value.replace(".","")
        list_limit_week.append(int(value) if value else 0)
    
    for i in range(duration):
        value = factor_week.get(i, 0)
        if value != 0:
            value = value.replace(".","")
        list_factor_week.append(int(value) if value else 0)

    obj_kilos = int(obj_kilos.replace(".",""))



    df = pd.read_excel("./generated_excel/Vendimia_historica.xlsx")

    df_select = df[df['AÑO'].isin(years_selected)] 

    kilos_delevered = df_select.groupby(['AÑO'])['KILOS ENTREGADOS'].sum().reset_index()

    kilos_delevered.rename(columns={"KILOS ENTREGADOS": "KILOS OBJETIVOS"}, inplace=True)

    df_select = pd.merge(df_select, kilos_delevered, on="AÑO", how= "left")

    df_week_kilos = df_select.groupby(['AÑO','NUM_SEMANA','KILOS OBJETIVOS'])['KILOS ENTREGADOS'].sum().reset_index()

    weekly_average = df_week_kilos.groupby('NUM_SEMANA')['KILOS ENTREGADOS'].mean()

    df_weekly_average = pd.DataFrame({'NUM_SEMANA': weekly_average.index, 'Promedio Kilos': np.round(weekly_average.values, 1)})

    df_pesos = pesos_semanal(1,duration, list_factor_week, obj_kilos, list_limit_week, df_weekly_average)
    df_salida = generar_semanas(1, duration, obj_kilos, list_limit_week, df_pesos,list_factor_week)

    df_salida.rename(columns={"NUM_SEMANA": "Semana", "Kilos_Entregar" : "Kilos"}, inplace=True)
    print(df_salida)
    df_json = df_salida.to_dict(orient="records")
    

    return jsonify({
        "message" : "Planificación realizada con exito",
        "data": df_json
    }), 200