#ifndef SOUND_MANAGER_H
#define SOUND_MANAGER_H

#include "Partitura.h"

// Definiciones de Registros de Hardware (Necesarias para la clase)
// Las direcciones de memoria de la GBA deben ser accedidas como punteros volátiles.

// Dirección base de los registros de E/S de la GBA
#define REG_BASE 0x04000000

#define REG_SOUNDCNT_X   *(volatile unsigned short*)(REG_BASE + 0x084)
#define REG_SOUNDCNT_H   *(volatile unsigned short*)(REG_BASE + 0x082)
#define REG_FIFO_A       *(volatile unsigned int*)(REG_BASE + 0x0A0)
#define REG_FIFO_B       *(volatile unsigned int*)(REG_BASE + 0x0A4)
#define REG_TM0CNT_H     *(volatile unsigned short*)(REG_BASE + 0x102)
#define REG_TM0CNT_L     *(volatile unsigned short*)(REG_BASE + 0x100)

// Constantes
#define SOUND_MASTER_ENABLE 0x0080 
#define DSA_ENABLE          0x0004
#define DSB_ENABLE          0x0040
#define TM_ENABLE           0x0080
#define SOUND_BASE_TIMER    65536 // Frecuencia más alta posible del Timer (para cálculo)

/**
 * @brief Clase Singleton que gestiona la reproducción de audio en la GBA.
 * Utiliza los canales Direct Sound (A y B) y un sistema de partitura (tracker).
 */
class SoundManager {
public:
    // Singleton Access
    static SoundManager& getInstance() {
        static SoundManager instance; // Se crea la primera y única instancia
        return instance;
    }

    // Prohibir copias y asignaciones (para mantener el Singleton)
    SoundManager(const SoundManager&) = delete;
    SoundManager& operator=(const SoundManager&) = delete;

    /**
     * @brief Inicializa el hardware de sonido y los Timers.
     */
    void init();

    /**
     * @brief Inicia la reproducción de una secuencia de TrackEvents.
     * @param track Puntero al array de TrackEvent de la partitura.
     */
    void startTrack(const TrackEvent* track);

    /**
     * @brief Lógica principal del motor: avanza la partitura y rellena los FIFOs.
     * Debe ser llamada en cada frame (o tick de interrupción).
     */
    void update();

private:
    // Variables de estado del motor de sonido
    const TrackEvent* m_currentTrack = nullptr;
    int m_trackIndex = 0;
    unsigned short m_noteDuration = 0;

    // Variables de estado de los canales A/B
    const signed char* m_sampleData[2] = {nullptr, nullptr};
    size_t m_samplePos[2] = {0, 0};
    size_t m_sampleLen[2] = {0, 0};

    // Constructor privado (Singleton)
    SoundManager() = default;

    /**
     * @brief Rellena el buffer FIFO de un canal Direct Sound (A o B).
     */
    void fillFIFO(int channelID);

    /**
     * @brief Configura e inicia la reproducción de una Sample en un canal.
     */
    void playSample(int channelID, const Sample& sample, int pitch);
};

#endif // SOUND_MANAGER_H