import os

def search_file(namefolder, namefile):
    folder = os.listdir(namefolder)
    files = [name for name in folder if os.path.isfile(os.path.join(namefolder,name))]
    for file in files:
        if file == namefile:
            return file
    
    else:
        return "Archivo no encontrado."

def rename_column(df, column_value):

    for y,x in column_value.items():
        print(y, x)

    return df