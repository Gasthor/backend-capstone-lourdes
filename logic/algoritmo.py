import pandas as pd


# Verifica y modifica de ser necesario los factores para complir y no sobre pasar los limites semanales de la bodega
def verificar_factores(df_semanas, kilos_objetivo, factor_semana, limite_kilos_semana):
  factor_semana_modificado = []
  print(df_semanas)
  for index,factor in enumerate(factor_semana):
    if index in df_semanas.index:
        kilos_factor = df_semanas.loc[index, "Porcentaje"] * (factor/100) * kilos_objetivo

        if kilos_factor > limite_kilos_semana[index]:
            kilos_semana = df_semanas.loc[index, "Porcentaje"] * kilos_objetivo
            nuevo_porcentaje = (df_semanas.loc[index, "Porcentaje"] * limite_kilos_semana[index])/kilos_semana
            df_semanas.loc[index, "Porcentaje"] = nuevo_porcentaje
            factor_semana_modificado.append(-100)

        else:
            factor_semana_modificado.append(factor_semana[index])
  print(factor_semana,factor_semana_modificado)
  return factor_semana_modificado

def pesos_semanal(inicio, fin, factor_semana, kilos_objetivo, limite_kilos_semana, df_promedio_semanal):
    df_semanas_seleccionadas = df_promedio_semanal[df_promedio_semanal['NUM_SEMANA'].between(inicio, fin)]
    total_kilos = df_semanas_seleccionadas['Promedio Kilos'].sum()
    df_semanas_seleccionadas.loc[:, 'Porcentaje'] = (df_semanas_seleccionadas['Promedio Kilos'] / total_kilos)

    factor_semana = verificar_factores(df_semanas_seleccionadas, kilos_objetivo, factor_semana, limite_kilos_semana)
    semanas_sin_factor = 0

    # Aplicar el factor a la semana correspondiente
    for index, factor in enumerate(factor_semana):
        if factor != 0 and factor != -100:
            df_semanas_seleccionadas.loc[index, "Porcentaje"] *= (factor / 100)
        elif factor == 0:
            semanas_sin_factor += 1

    # Calcular el porcentaje de exceso
    porcentaje_exceso = df_semanas_seleccionadas["Porcentaje"].sum()
    ####################################################################
    ajuste = (porcentaje_exceso - 1) / semanas_sin_factor if semanas_sin_factor > 0 else 0
    suma_exceso = 0
    semanas_0 = 0

    # Distribuir el ajuste en las semanas que no tienen factor
    for index, factor in enumerate(factor_semana):
        if factor == 0 and df_semanas_seleccionadas.loc[index, "Porcentaje"] - ajuste >= 0:
            df_semanas_seleccionadas.loc[index, "Porcentaje"] -= ajuste
        elif factor == 0 and df_semanas_seleccionadas.loc[index, "Porcentaje"] - ajuste < 0:
            suma_exceso += df_semanas_seleccionadas.loc[index, "Porcentaje"] - ajuste
            df_semanas_seleccionadas.loc[index, "Porcentaje"] = 0
            semanas_0 += 1

    if suma_exceso != 0:
        ajuste_exceso = suma_exceso / (semanas_sin_factor - semanas_0) if (semanas_sin_factor - semanas_0) > 0 else 0
        for index, factor in enumerate(factor_semana):
            if factor == 0 and df_semanas_seleccionadas.loc[index, "Porcentaje"] != 0 and df_semanas_seleccionadas.loc[index, "Porcentaje"] - ajuste_exceso >= 0:
                df_semanas_seleccionadas.loc[index, "Porcentaje"] += ajuste_exceso
        df_semanas_seleccionadas.loc[df_semanas_seleccionadas["Porcentaje"] < 0, "Porcentaje"] = 0

    return df_semanas_seleccionadas

class Semana:
    def __init__(self, num_semana, porcentaje, limite_kilos_semana, factor):
        self.num_semana = num_semana
        self.porcentaje = porcentaje
        self.limite_kilos_semana = limite_kilos_semana
        self.kilos_entregar = 0
        self.factor = factor

    def calcular_kilos_entregar(self, kilos_obj, kilos_excedentes):
        kilos_semana = round(self.porcentaje * kilos_obj * 100, 1)
        if kilos_semana + self.kilos_entregar > self.limite_kilos_semana:
            exceso = kilos_semana + self.kilos_entregar - self.limite_kilos_semana
            self.kilos_entregar = self.limite_kilos_semana
            kilos_excedentes += exceso
            return kilos_excedentes
        else:
            self.kilos_entregar =+ kilos_semana
            return kilos_excedentes

    def redistribuir_excedentes(self, kilos_excedentes):
        if kilos_excedentes > 0 and self.factor == False:
            espacio_disponible = self.limite_kilos_semana - self.kilos_entregar
            if espacio_disponible > 0 and self.porcentaje != 0:  # Se agrega esta validación
                kilos_a_redistribuir = min(espacio_disponible, kilos_excedentes)
                self.kilos_entregar += kilos_a_redistribuir
                kilos_excedentes -= kilos_a_redistribuir
        return kilos_excedentes

    def __str__(self):
        return f'Semana {self.num_semana}'

def buscar_semana_por_numero(numero, lista_semanas):
    for semana in lista_semanas:
        if semana.num_semana == numero:
            return semana
    return None

def generar_semanas(inicio, fin, kilos_obj, limite_kilos_semana, df_semanas_seleccionadas, factor_semana):
    semanas = []
    kilos_excedentes = 0
    kilos_repartidos = 0
    porcentajes_semana = df_semanas_seleccionadas.set_index('NUM_SEMANA')['Porcentaje'] / 100
    #se crean las semanas con los kilos segun sus porcentajes
    for num_semana in range(inicio, fin + 1):
        #Si hay kilos excedentes se verifica si se pueden asignar a la semana
        if kilos_excedentes > 0:
          kilos_excedentes = semana.redistribuir_excedentes(kilos_excedentes)

        porcentaje_semana = porcentajes_semana.get(num_semana, 0)
        
        semana = Semana(num_semana, porcentaje_semana, limite_kilos_semana[num_semana-1], False if factor_semana[num_semana-1] == 0 else True)
        kilos_excedentes = semana.calcular_kilos_entregar(kilos_obj, kilos_excedentes)
        kilos_repartidos += semana.kilos_entregar
        kilos_restantes = kilos_obj - kilos_repartidos
        #Se verifica que los kilos restantes no sea negativo
        if kilos_restantes < 0:
          kilos_semana = semana.kilos_entregar
          nuevo_porcentaje = ((kilos_semana + kilos_restantes) * semana.porcentaje *100) / kilos_semana
          semana.kilos_entregar = kilos_semana + kilos_restantes
          semana.porcentaje = nuevo_porcentaje
          df_semanas_seleccionadas.loc[num_semana - 1,'Porcentaje'] = nuevo_porcentaje
          kilos_repartidos = 0
        semanas.append(semana)

    #Se redistribuyen los kilos en las semanas anteriores
    if kilos_excedentes > 0:
      for semana in semanas[::-1]:
          kilos_excedentes = semana.redistribuir_excedentes(kilos_excedentes)

          if kilos_excedentes == 0:
              break

    df_semanas_kilos = pd.DataFrame([(semana.num_semana, semana.kilos_entregar) for semana in semanas],
                                     columns=['NUM_SEMANA', 'Kilos_Entregar'])
    df_semanas_kilos = df_semanas_kilos.merge(df_semanas_seleccionadas[['NUM_SEMANA', 'Porcentaje']], on='NUM_SEMANA', how='left')

    total_kilos_entregar = df_semanas_kilos['Kilos_Entregar'].sum()

    return df_semanas_kilos