enum class PokeBall {
    // Gen I (base, necesarias igual)
    POKE_BALL,
    GREAT_BALL,
    ULTRA_BALL,
    MASTER_BALL,

    // Gen II
    LEVEL_BALL,
    LURE_BALL,
    MOON_BALL,
    FRIEND_BALL,
    LOVE_BALL,
    FAST_BALL,
    HEAVY_BALL,
    SAFARI_BALL,

    // Gen III
    NEST_BALL,
    NET_BALL,
    DIVE_BALL,
    REPEAT_BALL,
    TIMER_BALL,
    LUXURY_BALL,
    PREMIER_BALL
};

double bonusBall(PokeBall ball,
                 int pokemonLevel = 1,
                 bool sameSpeciesCaught = false,
                 bool isWaterOrBug = false,
                 int turns = 1,
                 double weightLbs = 0.0) {
    switch (ball) {

    case PokeBall::POKE_BALL:
    case PokeBall::PREMIER_BALL:
    case PokeBall::LUXURY_BALL:
    case PokeBall::FRIEND_BALL:
        return 1.0;

    case PokeBall::GREAT_BALL:
        return 1.5;

    case PokeBall::ULTRA_BALL:
        return 2.0;

    case PokeBall::MASTER_BALL:
        return 255.0; // captura garantizada

    // ===== GEN II =====

    case PokeBall::LEVEL_BALL:
        if (pokemonLevel >= 40) return 4.0;
        if (pokemonLevel >= 20) return 2.0;
        return 1.0;

    case PokeBall::LURE_BALL:
        return 3.0; // solo si pesco

    case PokeBall::MOON_BALL:
        return 4.0; // solo especies evol. por Moon Stone

    case PokeBall::LOVE_BALL:
        return 8.0; // mismo species + sexo opuesto

    case PokeBall::FAST_BALL:
        return 4.0; // flee rate alto

    case PokeBall::HEAVY_BALL:
        // Gen II usa SUMA al rate, no multiplicador
        if (weightLbs > 903.0) return 1.3;
        if (weightLbs >= 677.3) return 1.2;
        return 0.8;

    case PokeBall::SAFARI_BALL:
        return 1.5;

    // ===== GEN III =====

    case PokeBall::NEST_BALL:
        return (pokemonLevel < 30)
            ? (30.0 - pokemonLevel) / 10.0
            : 1.0;

    case PokeBall::NET_BALL:
        return isWaterOrBug ? 3.0 : 1.0;

    case PokeBall::DIVE_BALL:
        return isWaterOrBug ? 3.5 : 1.0;

    case PokeBall::REPEAT_BALL:
        return sameSpeciesCaught ? 3.0 : 1.0;

    case PokeBall::TIMER_BALL:
        return std::min(4.0, 1.0 + 0.3 * turns);

    default:
        return 1.0;
    }
}
