# Plan de Cambios

Documento de trabajo para ir aplicando mejoras en el proyecto de forma ordenada.

## 1. Corregir lectura de POT/ADS en tiempo real

Prioridad: Alta

Objetivo:
- Hacer que la lectura en vivo de potenciómetros configurados como `ADS0`, `ADS1`, etc. funcione correctamente en el wizard y en la monitorización.

Problema detectado:
- El wizard usa pines tipo `ADS0` en `wizard/device_wizard.py`.
- `ConnectionManager` parsea `IO.STATE` convirtiendo siempre el pin a entero en `connection_manager.py`.
- Si el firmware devuelve `ADS0` como texto, la lectura en vivo del POT puede fallar.

Cambios recomendados:
- Revisar el parseo de `IO.STATE` en `connection_manager.py`.
- Permitir que el pin pueda ser entero o token tipo `ADSx`.
- Verificar que `LivePinTester` y `DeviceWizard` comparen el pin con el mismo formato.
- Probar lectura real y simulada.

Checklist:
- [OK] Ajustar parser de `IO.STATE`
- [OK] Unificar formato de pin para POT/ADS
- [ ] Verificar wizard de prueba de pin
- [ ] Verificar captura de valor en muescas

## 2. Completar la funcionalidad de muescas del POT

Prioridad: Alta

Objetivo:
- Conseguir que la configuración de muescas no solo exista en la UI, sino también en persistencia y generación de comandos.

Problema detectado:
- El wizard permite definir muescas.
- Esas muescas se guardan como atributos dinámicos del objeto.
- El modelo actual no las serializa.
- El guardado JSON no las conserva.
- La generación de comandos no las envía al dispositivo.

Cambios recomendados:
- Extender el modelo `Device` o migrar a un modelo más completo.
- Guardar `pot_notches_enabled` y `pot_notches` en `to_dict` / `from_dict`.
- Ajustar `storage.py` para que no se pierda información.
- Ampliar `command_builder.py` si el firmware soporta comandos para muescas.
- Confirmar primero cuál es el comando real esperado por el firmware.

Checklist:
- [ ] Definir estructura persistente para muescas
- [ ] Guardar/cargar muescas en JSON
- [ ] Mostrar muescas al recargar proyecto
- [ ] Generar comandos para muescas si aplica
- [ ] Validar compatibilidad con firmware

## 3. Guardar y cargar proyecto completo

Prioridad: Alta

Objetivo:
- Tener un único archivo de proyecto con la configuración EasySim y Modbus.

Problema detectado:
- Actualmente `save_json` y `load_json` trabajan solo con `self.devices`.
- La configuración Modbus se mantiene aparte dentro de `modbus_widget`.
- El usuario puede pensar que guarda todo, pero hoy no es así.

Cambios recomendados:
- Diseñar un formato de proyecto único.
- Incluir:
  - dispositivos EasySim
  - esclavos Modbus
  - tags Modbus
- Añadir versionado simple al JSON para futuras migraciones.
- Hacer que `save_json` y `load_json` lean y escriban el proyecto completo.

Checklist:
- [ ] Definir esquema de proyecto
- [ ] Guardar dispositivos EasySim
- [ ] Guardar dispositivos Modbus
- [ ] Guardar tags Modbus
- [ ] Cargar todo en la UI correctamente
- [ ] Añadir campo `version`

## 4. Unificar el modelo de datos

Prioridad: Media

Objetivo:
- Evitar que convivan dos modelos de dispositivo con responsabilidades parecidas.

Problema detectado:
- Existe `models/device.py` como modelo activo.
- Existe `models/device_config.py` como modelo más rico, pero no está integrado.
- Esto sugiere una transición incompleta o una refactorización a medias.

Cambios recomendados:
- Elegir una estrategia:
  - mantener `Device` y ampliarlo, o
  - migrar todo a `DeviceConfig`
- Eliminar modelo muerto o dejar clara su función.
- Ajustar wizards, storage y command builder al modelo elegido.

Checklist:
- [ ] Decidir modelo definitivo
- [ ] Migrar usos del modelo
- [ ] Eliminar duplicidad innecesaria
- [ ] Verificar compatibilidad con JSON existente

## 5. Centralizar `normalize_kind`

Prioridad: Media

Objetivo:
- Tener una sola implementación para normalizar tipos de dispositivo.

Problema detectado:
- `normalize_kind` está duplicado en varios archivos.
- Esto aumenta el riesgo de que una versión se actualice y otra no.

Cambios recomendados:
- Crear una utilidad compartida, por ejemplo en `utils` o en un módulo de dominio.
- Sustituir las copias locales por imports.

Checklist:
- [ ] Crear función común
- [ ] Reemplazar duplicados
- [ ] Verificar que no cambie el comportamiento

## 6. Reducir acoplamiento de `MainWindow`

Prioridad: Media

Objetivo:
- Hacer que la ventana principal coordine la app sin concentrar toda la lógica de negocio.

Problema detectado:
- `main_window.py` mezcla:
  - UI
  - parseo de `#DUMP`
  - persistencia
  - envío de comandos
  - coordinación con Modbus

Cambios recomendados:
- Extraer al menos:
  - servicio de persistencia de proyecto
  - parser de configuración recibida
  - coordinador o builder de envío completo

Checklist:
- [ ] Identificar bloques extraíbles
- [ ] Mover parser de dump
- [ ] Mover persistencia de proyecto
- [ ] Simplificar `MainWindow`

## 7. Añadir tests de regresión

Prioridad: Media-Baja

Objetivo:
- Proteger las partes más sensibles antes de seguir ampliando funcionalidad.

Áreas recomendadas:
- `commands/command_builder.py`
- `storage.py`
- parser de `#DUMP`
- parser de líneas Modbus

Checklist:
- [ ] Añadir estructura base de tests
- [ ] Test de guardado/carga
- [ ] Test de generación de comandos
- [ ] Test de parseo de dump
- [ ] Test de parseo Modbus

## 8. Revisar persistencia del borrado en hardware

Prioridad: Media-Baja

Objetivo:
- Confirmar que borrar desde la UI realmente deja el equipo en estado persistente.

Problema detectado:
- El borrado envía `#CONFIG`, comando de borrado y `#END`.
- Puede que falte `#SAVE`, dependiendo de cómo funcione el firmware.

Cambios recomendados:
- Revisar el contrato del firmware.
- Si hace falta, incluir guardado explícito después del borrado.
- Probar borrado real, reinicio y relectura con `#DUMP`.

Checklist:
- [ ] Confirmar comportamiento del firmware
- [ ] Añadir `#SAVE` si aplica
- [ ] Validar borrado tras reinicio

## Orden recomendado de ejecución

1. Corregir lectura de POT/ADS en tiempo real
2. Completar la funcionalidad de muescas del POT
3. Guardar y cargar proyecto completo
4. Unificar el modelo de datos
5. Centralizar `normalize_kind`
6. Reducir acoplamiento de `MainWindow`
7. Añadir tests de regresión
8. Revisar persistencia del borrado en hardware

## Siguiente paso sugerido

Empezar por el bloque 1 porque es el cambio con mejor relación entre impacto y riesgo.
