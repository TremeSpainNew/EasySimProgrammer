# EasySim Programmer Qt

Versión compacta del programador EasySim.

## Ejecutar

```bash
pip install -r requirements.txt
python main.py
```

Incluye:

- Tablas separadas por tipo.
- Wizard compacto tipo instalador.
- Prueba visual de pines.
- Simulación.
- TCP básico.
- Serial básico.
- OTA por Bluetooth BLE.
- Guardar/cargar JSON.
- Generar/enviar comandos.

Dependencias nuevas:

- `bleak` para descubrir el dispositivo `EASYSIM-OTA` y enviar el firmware por BLE.
