# Tablero de dispensación de medicamentos

Dashboard interactivo para explorar los registros de dispensación de medicamentos de una EPS, con datos de enero de 2020 a noviembre de 2021. El proyecto forma parte del curso **Toma de decisiones basada en datos** y se centra en costos, personas, fórmulas, cobertura PBS, modalidad de entrega, geografía y antidiabéticos.

## Contenido del proyecto

- `app_medicamentos.py`: aplicación Dash, consultas SQL y callbacks de interacción.
- [Código fuente en GitHub](https://github.com/AngelVR23/Tablero_Dispensaci-n_medicamentos/blob/main/app_medicamentos.py).
- `medicamentos.db`: base SQLite con la tabla `dispensacion`.
- `requirements.txt`: dependencias de la aplicación y de las figuras del informe.
- `Tablero_medicamentos.qmd`: informe reproducible, con metodología, resultados, gráficas y espacio para el enlace de ejecución.
- `Imagen1.jpg`: imagen institucional para la portada del informe.

## Funcionalidad

La vista **Resumen general** permite filtrar por año, mes, grupo farmacológico y regional CAF. Presenta KPI, evolución mensual, top de medicamentos, distribución PBS/No PBS, gasto por departamento y modalidad de entrega, mapa municipal, distribución por grupo y una tabla con hasta 200 registros recientes. La gráfica de modalidades incluye barras por año y el total del periodo para cada tipo de entrega.

La vista **Antidiabéticos** presenta indicadores, comparación de años sobre meses comparables, evolución mensual, composición insulinas/orales, top de medicamentos y precios unitarios. Esta vista ignora los filtros generales de año, mes y grupo, pero conserva la regional seleccionada.

## Lógica de datos

La aplicación consulta SQLite mediante agregaciones SQL en lugar de cargar la tabla completa en memoria. Una vista temporal deriva año, mes y periodo; reemplaza campos geográficos faltantes o con código `0` por `SIN REGISTRO`; y completa grupos farmacológicos vacíos usando la clasificación disponible para la misma descripción del medicamento. Los filtros se envían como parámetros SQL.

Los KPI principales se calculan como identificadores distintos de persona (`id`), fórmulas distintas (`formula`), suma de `costo_total` y costo total dividido entre las fórmulas distintas. La clasificación recuperada es una regla de preparación asumida y debe validarse con conocimiento del dominio.

## Requisitos

- Python 3.10 o posterior.
- Quarto y una distribución LaTeX para producir el PDF.
- Un kernel Jupyter de Python que use el mismo entorno donde se instalan las dependencias.

## Instalación y ejecución local

En PowerShell, desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app_medicamentos.py
```

Abrir `http://127.0.0.1:8050/` en el navegador. En otros sistemas, activar el entorno virtual con el comando correspondiente al sistema operativo.

## Renderizar el informe PDF

Con Quarto y LaTeX instalados, y el kernel `python3` configurado para el entorno que tiene las dependencias:

```powershell
quarto render Tablero_medicamentos.qmd --to pdf
```

Quarto crea `Tablero_medicamentos.pdf` en esta misma carpeta. `Imagen1.jpg`, `cover.tex` y `header.tex` deben permanecer junto al documento. La portada y el anexo enlazan a la aplicación pública de Posit. El informe no duplica el código fuente: este se conserva en `app_medicamentos.py`.

## Despliegue

La aplicación expone el servidor Flask de Dash como `server` para facilitar despliegues WSGI. El tablero publicado está en [Posit Connect](https://01a0e88b-5124-bf26-d105-4bb9c7ce5b09.share.connect.posit.cloud/), y el código fuente está enlazado en GitHub. El comando o mecanismo de publicación depende del servicio escogido; `gunicorn` está incluido en los requisitos para plataformas que lo necesiten, pero no es necesario para ejecutar localmente con `python app_medicamentos.py`.

## Alcance y limitaciones

Los datos llegan hasta noviembre de 2021, así que el total de 2021 no cubre un año completo. Hay registros sin información regional/geográfica y las coordenadas del mapa son aproximadas. El tablero es descriptivo; sus resultados no representan inferencia causal ni recomendación clínica.
