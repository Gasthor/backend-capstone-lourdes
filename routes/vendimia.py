from datetime import timedelta
from flask import Blueprint, json, jsonify, request
import numpy as np
import pandas as pd

from logic.algoritmo import generar_semanas, pesos_semanal
from logic.files import search_file

import locale

try:
    locale.setlocale(locale.LC_TIME, 'es_ES.utf-8')
except locale.Error:
    locale.setlocale(locale.LC_TIME, 'C')

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

    # Agrupar por semana y año, y sumar los kilos entregados
    df_grouped = df_select.groupby(["NUM_SEMANA", "AÑO"])["KILOS ENTREGADOS"].sum().reset_index()
    df_grouped = df_grouped.rename(columns={"NUM_SEMANA": "Semana", "KILOS ENTREGADOS": "Kilos"})

    # Encontrar la fecha mínima para cada combinación de semana y año
    df_min_date = df_select.groupby(["NUM_SEMANA", "AÑO"])["FECHA"].min().reset_index()
    df_min_date = df_min_date.rename(columns={"NUM_SEMANA": "Semana", "FECHA": "Fecha_inicio"})

    # Fusionar la fecha mínima con el DataFrame agrupado
    df_grouped = pd.merge(df_grouped, df_min_date, on=["Semana", "AÑO"], how="left")

    # Agregar columna del día de la semana en español
    df_grouped['Dia'] = df_grouped['Fecha_inicio'].dt.day_name(locale='es_ES.utf-8')
    df_grouped['Mes'] = df_grouped['Fecha_inicio'].dt.month_name(locale='es_ES.utf-8')

    # Promedio de kilos por semana
    df_resumen = df_grouped.groupby(["Semana"])["Kilos"].mean().reset_index()

    # Calcular lista de años, días y meses en español por semana
    df_grouped['AÑO_Mes_Dia'] = df_grouped.apply(lambda row: [row['AÑO'],row['Fecha_inicio'].strftime('%d'), row['Dia'], row['Mes']], axis=1)
    df_list = df_grouped.groupby('Semana')['AÑO_Mes_Dia'].apply(list).reset_index(name='Years')

    # Fusionar la lista de años, días y meses con el DataFrame resumen
    df_resumen = pd.merge(df_resumen, df_list, on="Semana", how="left")
    print(df_grouped)
    # Convertir a formato JSON
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

    formatted_years = ' - '.join(map(str, years))
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

    try:
        df_pesos = pesos_semanal(1,duration, list_factor_week, obj_kilos, list_limit_week, df_weekly_average)
        df_salida = generar_semanas(1, duration, obj_kilos, list_limit_week, df_pesos,list_factor_week)
    except Exception as e:
        return jsonify({
        "message" : f"Error en calcular semanas, mensaje error: ${e}",
    }), 400
    df_salida['Porcentaje'] = df_salida['Porcentaje'].fillna(0)

    df_salida.rename(columns={"NUM_SEMANA": "Semana", "Kilos_Entregar" : "Kilos"}, inplace=True)

    total = int(df_salida["Kilos"].sum())
    
    df_json = df_salida.to_dict(orient="records")
    ######################################################




    ######################################################
    
    ranking = df_select.groupby(["NUM_SEMANA", "AREA", "FAMILIA"])["KILOS ENTREGADOS"].sum().reset_index()

    total_kilos = df_select.groupby(["NUM_SEMANA"])["KILOS ENTREGADOS"].sum().reset_index()

    total_kilos.rename(columns={"KILOS ENTREGADOS": "TOTAL_KILOS"}, inplace=True)

    ranking_con_total = pd.merge(ranking, total_kilos, on=["NUM_SEMANA"])

    ranking_con_total["PORCENTAJE_PARTICIPACION"] = (ranking_con_total["KILOS ENTREGADOS"] / ranking_con_total["TOTAL_KILOS"]) * 100

    ranking_con_total.rename(columns={"KILOS ENTREGADOS": "KILOS_ENTREGADOS"}, inplace=True)

    ranking_con_total.columns = ranking_con_total.columns.str.strip()

    if len(years_selected) > 1:

        ranking_con_total["KILOS_ENTREGADOS"] = ranking_con_total["KILOS_ENTREGADOS"] / len(years_selected)

    ranking_con_total["KILOS_ENTREGADOS"] = ranking_con_total["KILOS_ENTREGADOS"].apply(lambda x: f"{x:,.0f} kg")

    ranking_con_total["PORCENTAJE_PARTICIPACION"] = ranking_con_total["PORCENTAJE_PARTICIPACION"].round(2)

    # Calcular el porcentaje de participación por familia
    por_familia = ranking_con_total.groupby(["FAMILIA", "NUM_SEMANA"])["PORCENTAJE_PARTICIPACION"].sum().reset_index()
    por_familia.rename(columns={"PORCENTAJE_PARTICIPACION": "POR_FAMILIA"}, inplace=True)

    # Fusionar el porcentaje de participación por familia de nuevo en el DataFrame original
    ranking_con_total = pd.merge(ranking_con_total, por_familia, on=["FAMILIA", "NUM_SEMANA"], how='left')

    ranking_con_total = ranking_con_total.sort_values(by=["NUM_SEMANA", "POR_FAMILIA", "PORCENTAJE_PARTICIPACION"], ascending=[True, False, False])

    print(ranking_con_total.head(30))

    ranking_json = ranking_con_total.to_dict(orient="records")

    contract_producer = df_select.groupby(["CONTRATO","FAMILIA","AREA","PRODUCTOR", "NUM_SEMANA"])["KILOS ENTREGADOS"].sum().reset_index()

    contract_producer = contract_producer.rename(columns={"KILOS ENTREGADOS" : "KILOS_ENTREGADOS"}, inplace=False)
    
    contract_producer["KILOS_ENTREGADOS"] = contract_producer["KILOS_ENTREGADOS"].apply(lambda x: f"{x:,.0f} kg")

    contract_producer = contract_producer.to_dict(orient="records")
    

    ##############################################################
    return jsonify({
        "message" : "Planificación realizada con exito",
        "data": df_json,
        "total": total,
        "ranking" : ranking_json,
        "years" : years_selected,
        "contract_producer" : contract_producer
    }), 200