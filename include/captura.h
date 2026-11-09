#ifndef CAPTURA_H
#define CAPTURA_H

#include <cmath>
#include <algorithm>
#include <cstdint>

/* =========================================================
   CORE GEN III
   ========================================================= */

inline double calcularA(double hpMax, double hpActual, double rate, double bonusBall, double bonusStatus) {
    double a = ((3.0 * hpMax - 2.0 * hpActual) * rate * bonusBall)
               / (3.0 * hpMax)
               * bonusStatus;

    return std::clamp(a, 1.0, 255.0);
}

/* =========================================================
   PROBABILIDAD TEÓRICA (UI / STATS)
   ========================================================= */

inline double probabilidadCapturaTeorica(double a) {
    if (a >= 255.0)
        return 1.0;

    return std::pow(a / 255.0, 4);
}

inline double pokeballsEsperadas(double p) {
    return 1.0 / p;
}

/* =========================================================
   CAPTURA REAL GEN 3 
   ========================================================= */

inline bool captura(double a, uint8_t r1, uint8_t r2, uint8_t r3, uint8_t r4) {

    if (a >= 255.0)
        return true;
    return r1 < a &&  r2 < a && r3 < a && r4 < a;
}

/* =========================================================
   BONUS DE ESTADO GEN 3
   ========================================================= */

inline double bonusEstado(bool sleepFreeze, bool paralyzePoisonBurn) {
    if (sleepFreeze) return 2.0;
    if (paralyzePoisonBurn) return 1.5;
    return 1.0;
}

/* =========================================================
   BALLS
   ========================================================= */

/* Heavy Ball*/
inline double bonusHeavyBall(double pesoLbs) {
    if (pesoLbs < 451.5) return -20.0;
    if (pesoLbs >= 677.3 && pesoLbs <= 903.0) return 20.0;
    if (pesoLbs > 903.0) return 30.0;
    return 0.0;
}

/* Multiplicadores
   Ultra = 2.0, Net = 3.0, etc */
inline double multiplicadorBall(double mult) {
    return mult;
}

/* =========================================================
   SAFARI ZONE
   ========================================================= */

struct SafariEstado {
    double modCatch = 1.0;
    double modFlee  = 1.0;
};

inline void safariComer(SafariEstado& s) {
    s.modCatch *= 1.3;
    s.modFlee  *= 0.8;
}

inline void safariPiedra(SafariEstado& s) {
    s.modCatch *= 1.5;
    s.modFlee  *= 1.8;
}

/* =========================================================
   PIPELINE FINAL DE CAPTURA
   ========================================================= */

inline bool capturaFinal( double hpMax, double hpActual, double rateBase, double pesoLbs, PokeBall ball,
    int pokemonLevel, bool sameSpeciesCaught, bool isWaterOrBug, int turns, double bonusStatus, 
    const SafariEstado& safari,uint8_t r1, uint8_t r2, uint8_t r3, uint8_t r4) {
    
    /* Catch rate  */
    double rate = rateBase;

    /* Heavy Ball*/
    if (ball == PokeBall::HEAVY_BALL) {
        rate += bonusHeavyBall(pesoLbs);
    }

    rate = std::clamp(rate, 1.0, 255.0);

    /* Multiplicador  */
    double ballMult = bonusBall( ball, pokemonLevel, sameSpeciesCaught, isWaterOrBug, turns, pesoLbs);

    
    double a = calcularA( hpMax, hpActual, rate, ballMult * safari.modCatch, bonusStatus);

    return capturaGenIII(a, r1, r2, r3, r4);
}

#endif // CAPTURA_H
