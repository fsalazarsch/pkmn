#ifndef PARTITURA_H
#define PARTITURA_H

#include <cstddef> // Para size_t

/**
 * @brief Estructura que define un 'instrumento' (muestra de audio PCM).
 * El audio debe ser raw de 8 bits.
 */
struct Sample {
    const signed char* data; // Puntero a la data de la muestra (array)
    size_t length;           // Longitud total de la muestra en bytes
};

struct TrackEvent {
    int sample_id;           // ID del Instrumento a usar (índice en el catálogo)
    int pitch;               // Valor del Timer (Pitch) para establecer el tono.
    unsigned short duration; // Duración de la nota en 'frames' (ticks)
};

// =========================================================
// CATÁLOGO DE INSTRUMENTOS (Se define en tu archivo de datos)
// Debes declarar el array global aquí para que SoundManager pueda acceder a él.
// =========================================================

extern const Sample INSTRUMENTS_CATALOG[];
extern const size_t NUM_INSTRUMENTS;

enum InstrumentID {
    INST_PIANO_C4 = 0,
    INST_DRUM_KICK = 1,
    INST_FLUTE_C6 = 2,
};

#endif // PARTITURA_H