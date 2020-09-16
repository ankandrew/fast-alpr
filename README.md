# ConvALPR


[![Alt Text](imgs/demo_alpr.gif)](https://youtu.be/-TPJot7-HTs?t=652)

**ConvALPR** es un Reconocedor Automatico de Patentes Vehiculares, que utiliza **Redes Neuronales Convolucionales**. A diferencia de metodos tradicionales, este approach puede reconocer patentes cuando estas tienen obstrucciones/diferencia de brillo/letras borrosas, etc. Este reconocedor consiste de dos etapas: **localizar** (detector de objetos) y **reconocedor** (Reconocimiento Optico de Caracteres). Ambas usan solamente **Redes Convolucionales/ConvNets/CNNs**.

*Aclaracion: Si bien el localizador funciona para patentes de cualquier pais el reconocedor actual esta hecho especialmente para **Argentina**,
 si queres entrenar uno [desde cero](https://github.com/ankandrew/cnn-ocr-lp/wiki/Entrenamiento)*

### Localizador

Para el **localizador** se usa yolo v4 **[tiny](https://github.com/AlexeyAB/darknet#yolo-v4-v3-and-v2-for-windows-and-linux)**, para lograr que el detector corra en **tiempo real**. Este detector de objetos se entreno con patentes (ni una sola de Argentina) aun asino tiene problemas en localizarlas con alta precision. Mas detalles de entrenamiento del detector **[aca](https://github.com/ankandrew/LocalizadorPatentes)**. Se convirtieron los parametros de framework Darknet a TensorFlow usando este **[repo](https://github.com/hunglc007/tensorflow-yolov4-tflite)**. 


En este repo se pueden encontrar **3** versiones del localizador de patentes, misma arquitectura (**yolo v4 tiny sin spp**), pero con distinta resolucion de entrada. Los modelos usan res. de entrada de {*384x384*, *512x512*, *608x608*}, donde a mayor la resolucion **mayor es la precision** (y puede detectar mejor patentes alejadas) pero mayor es el tiempo de inferencia (es **mas lento**). Estos modelos se encuentran [`alpr/models/detection`](alpr/models/detection/)

### Reconocedor (ROC/OCR)

Para el **reconocedor de caracteres** [OCR](https://es.wikipedia.org/wiki/Reconocimiento_%C3%B3ptico_de_caracteres) de las patentes, se diseñaron unos modelos personalizados en TensorFlow Keras. 

En este repositorio se pueden encontrar los mismos modelos que [aca](https://github.com/ankandrew/cnn-ocr-lp). Estos modelos se pueden encontrar tambien en [`alpr/models/ocr`](alpr/models/ocr/), y los modelos que tienen `_CPU` al final esta mejor optimizados para CPU y corren mas rapido en el procesador.

### Localizador + Reconocedor = ALPR

![Proceso ALPR](imgs/proceso.png)

## Como usarlo

### Instalar dependencias

Con python **3.x**:

```
pip install -r requirements.txt
```

Para correr con la **placa de video/GPU** y acelerar la inferencia, instalar estos **[requerimientos](https://www.tensorflow.org/install/gpu#software_requirements)**.

### Visualizar solo localizador

Para probar el **localizador/detector** de patentes (**sin OCR**) y visualizar las predicciones se usa el comando:

```
python detector_demo.py --fuente-video /path/a/tu/video.mp4 --mostrar-resultados --input-size 608
```

*Intenta con los distintos modelos {608, 512, 384} para ver cual se ajusta mejor a tu caso*

#### Demo Salida

![Demo yolo v4 tiny](imgs/demo_localizador.gif)

## Reconocedor Automatico

### Config

La **configuracion** del [ALPR](https://es.wikipedia.org/wiki/Reconocimiento_autom%C3%A1tico_de_matr%C3%ADculas) se puede encontrar en [`config.yaml`](config.yaml). Este contiene los ajustes del Reconocedor y Localizador. Las distintas opciones estan descriptas en el mismo archivo (que hacen). El modelo de OCR es **independiente** del detector de objetos, y cualquiera deberia funcionar bien con cualquiera. Ejemplo para correr en la CPU y *priorizar velocidad*, se puede elegir el modelo 3 o 4 y el detector 384. Si se prefiere **mayor precision** se puede elegir el detector con res. de entrada 608 y OCR 1 o 2.

### Ejemplo visualizar ALPR

```
python reconocedor_automatico.py --cfg config.yaml --demo
```

### Guarda en Base de Datos sin visualizar

```
python reconocedor_automatico.py --cfg config.yaml
```

### Visualizar prediccion de imagen y mostras FPS

En el archivo de config en la fuente poner una imagen. Luego

```
python reconocedor_automatico.py --cfg config.yaml --imagen --benchmark
```

## TODO

- [ ] Ampliar modelos OCR
- [ ] Compilar para EdgeTPU
- [ ] Quantizar a FP16
- [ ] Quantizar a INT8
- [ ] Optimizar