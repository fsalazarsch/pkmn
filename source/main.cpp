extern "C" {
    #include <tonc.h>
    #include "tileset_data.h"
    #include "world.h"
    #include "player_data.h"
    #include "tile_behavior.h"
}

//---------------------------------------------------------------------------------
// Constantes
//---------------------------------------------------------------------------------
#define TILE_PX      16                          // 1 "casilla" del juego = 16x16 px
#define WORLD_MAX_W  32                          // ancho máximo del mundo en casillas

#define OBJ_SBB      24                          // BG1 (objetos): screenblocks 24..27
#define GROUND_SBB   28                          // BG0 (suelo):   screenblocks 28..31
#define BG_ROWS      64                          // alto del BG en tiles de 8x8
#define TILE_BUDGET  768                         // tiles 8bpp que caben antes del screenblock 24

#define TURN_FRAMES  8                          // frames que hay que mantener el botón para empezar a caminar tras girar

#define NOT_LOADED   0xFFFF
#define NO_ROW       (-1000)                     // "esta fila del BG aún no se ha cargado"


enum Dir { DIR_DOWN = 0, DIR_UP = 1, DIR_LEFT = 2, DIR_RIGHT = 3 };

struct Player
{
    int  tx, ty;      // casilla actual
    int  wx, wy;      // posición en píxeles del mundo (esquina sup. izq. de la casilla)
    Dir  dir;
    bool moving;
    int  step;        // 0..15
    int  phase;       // alterna pie izquierdo / derecho
    int  turn;        // frames de espera tras girar (si se suelta el botón, solo gira)
    bool hop;         // ¿está saltando un saliente?
    int  len;         // píxeles que dura el movimiento actual (16 caminar, 32 saltar)
};

static Player player;
static OBJ_ATTR *playerObj = &oam_mem[0];

//---------------------------------------------------------------------------------
// Tiles: de los 1730 de la colección, solo se copian a VRAM los que usa esta ruta
//---------------------------------------------------------------------------------
static unsigned short remap[TILESET_TILE_COUNT];   // tile de la colección -> tile en VRAM
static int nextTile;

static int vram_tile(int t)
{
    if (remap[t] == NOT_LOADED)
    {
        if (nextTile >= TILE_BUDGET)
            return 0;                                // sin espacio: se ve vacío
        memcpy32((void*)(MEM_VRAM + nextTile * 64), &tilesetTiles[t * 64], 64 / 4);
        remap[t] = nextTile++;
    }
    return remap[t];
}

static inline int safe_id(int id)
{
    return (id >= 0 && id < TILESET_META_COUNT) ? id : 0;
}

// Busca la casilla (tx, ty) del mundo en los mapas colocados.
// Devuelve false si ahí no hay ningún mapa.
static bool world_ids(int tx, int ty, int &g, int &o)
{
    for (int i = 0; i < worldMapCount; i++)
    {
        const MapPlacement &m = worldMaps[i];
        int x = tx - m.ox;
        int y = ty - m.oy;

        if (x >= 0 && x < m.w && y >= 0 && y < m.h)
        {
            g = m.ground[y * m.w + x];
            o = m.objects[y * m.w + x];
            return true;
        }
    }
    return false;
}

// Qué hay en una casilla: se mira el suelo y el objeto que tiene encima
static int cell_behavior(int tx, int ty)
{
    int gi, oi;
    if (!world_ids(tx, ty, gi, oi))
        return BEH_BLOCK;                            // fuera de todos los mapas

    int g = tileBehavior[safe_id(gi)];
    int o = tileBehavior[safe_id(oi)];

    if (g == BEH_BLOCK || o == BEH_BLOCK) return BEH_BLOCK;
    if (g == BEH_LEDGE || o == BEH_LEDGE) return BEH_LEDGE;
    return BEH_WALK;
}

static void load_world_tiles()
{
    for (int i = 0; i < TILESET_TILE_COUNT; i++)
        remap[i] = NOT_LOADED;

    memset32((void*)MEM_VRAM, 0, 64 / 4);            // tile 0 = vacío
    remap[0] = 0;
    nextTile = 1;

    for (int i = 0; i < worldMapCount; i++)
    {
        const MapPlacement &m = worldMaps[i];
        for (int n = 0; n < m.w * m.h; n++)
            for (int k = 0; k < 4; k++)
            {
                vram_tile(tilesetMeta[safe_id(m.ground[n])][k]);
                vram_tile(tilesetMeta[safe_id(m.objects[n])][k]);
            }
    }
}

//---------------------------------------------------------------------------------
// Fondo: el BG guarda 64 filas de tiles de 8x8; las filas se cargan "en streaming"
// a medida que la cámara sube o baja.
//---------------------------------------------------------------------------------
static int slotRow[BG_ROWS];       // qué fila del mapa hay en cada fila del BG

static void load_layer_row(int sbbBase, bool objectsLayer, int r)
{
    int slot = r & (BG_ROWS - 1);
    int sub  = (r & 1) << 1;              // 0 = mitad de arriba, 2 = mitad de abajo

    for (int x = 0; x < 64; x++)
    {
        int t = 0;
        int g, o;
        if (r >= 0 && world_ids(x >> 1, r >> 1, g, o))
        {
            int id = safe_id(objectsLayer ? o : g);
            t = remap[tilesetMeta[id][sub + (x & 1)]];
        }
        int sb  = sbbBase + (x >> 5) + ((slot >> 5) << 1);
        int idx = ((slot & 31) << 5) + (x & 31);
        se_mem[sb][idx] = t;
    }
}

static void load_row(int r)
{
    load_layer_row(GROUND_SBB, false, r);
    load_layer_row(OBJ_SBB,    true,  r);
    slotRow[r & (BG_ROWS - 1)] = r;
}

static void update_rows(int camY)
{
    int top = camY >> 3;
    for (int r = top; r <= top + 21; r++)
        if (slotRow[r & (BG_ROWS - 1)] != r)
            load_row(r);
}

//---------------------------------------------------------------------------------
// Inicialización
//---------------------------------------------------------------------------------
static void init_video()
{
    REG_DISPCNT = DCNT_BLANK;

    // Paleta de fondo (una sola para toda la colección)
    memcpy16(pal_bg_mem, tilesetPal, TILESET_PAL_LEN / 2);

    // Screenblocks de BG1 en blanco (los de BG0 se llenan por filas)
    memset32(&se_mem[OBJ_SBB][0], 0, 4096);

    load_world_tiles();

    for (int i = 0; i < BG_ROWS; i++)
        slotRow[i] = NO_ROW;

    // BG0 = suelo (atrás), BG1 = objetos (delante del suelo, detrás del jugador)
    REG_BG0CNT = BG_CBB(0) | BG_SBB(GROUND_SBB) | BG_8BPP | BG_REG_64x64 | BG_PRIO(2);
    REG_BG1CNT = BG_CBB(0) | BG_SBB(OBJ_SBB)    | BG_8BPP | BG_REG_64x64 | BG_PRIO(1);

    // Sprites (4bpp): tiles en charblock 4, paleta de OBJ banco 0
    memcpy32(&tile_mem[4][0], playerTiles, PLAYER_TILES_LEN / 4);
    memcpy16(pal_obj_mem, playerPal, 16);

    oam_init(oam_mem, 128);
    obj_set_attr(playerObj,
                 ATTR0_TALL | ATTR0_4BPP,          // 16x32
                 ATTR1_SIZE_32,
                 ATTR2_PALBANK(0) | ATTR2_ID(0) | ATTR2_PRIO(0));
}

static void init_player()
{
    player.tx = worldStartX;
    player.ty = worldStartY;
    player.wx = player.tx * TILE_PX;
    player.wy = player.ty * TILE_PX;
    player.dir = DIR_UP;
    player.moving = false;
    player.step = 0;
    player.phase = 0;
    player.turn = 0;
    player.hop = false;
    player.len = TILE_PX;
}

//---------------------------------------------------------------------------------
// Lógica
//---------------------------------------------------------------------------------
static void update_player()
{
    static const int DX[4] = {  0,  0, -1,  1 };
    static const int DY[4] = {  1, -1,  0,  0 };

    if (!player.moving)
    {
        int d = -1;
        if      (key_is_down(KEY_UP))    d = DIR_UP;
        else if (key_is_down(KEY_DOWN))  d = DIR_DOWN;
        else if (key_is_down(KEY_LEFT))  d = DIR_LEFT;
        else if (key_is_down(KEY_RIGHT)) d = DIR_RIGHT;

        if (d >= 0)
        {
            if (d != player.dir)
            {
                // Primero solo gira: si el botón se suelta antes, no avanza
                player.dir  = (Dir)d;
                player.turn = TURN_FRAMES;
            }
            else if (player.turn > 0)
            {
                player.turn--;
            }
            else
            {
                int nx = player.tx + DX[d];
                int ny = player.ty + DY[d];
                int b  = cell_behavior(nx, ny);

                if (b == BEH_WALK)
                {
                    player.moving = true;
                    player.hop    = false;
                    player.len    = TILE_PX;
                    player.step   = 0;
                }
                else if (b == BEH_LEDGE && d == DIR_DOWN &&
                         cell_behavior(nx, ny + 1) != BEH_BLOCK)
                {
                    // Saliente: solo se cruza hacia abajo y cae 2 casillas más allá
                    player.moving = true;
                    player.hop    = true;
                    player.len    = TILE_PX * 2;
                    player.step   = 0;
                }
                // BEH_BLOCK (o saliente desde otro lado): se queda mirando, sin avanzar
            }
        }
        else
        {
            player.turn = 0;
        }
    }

    if (player.moving)
    {
        player.wx += DX[player.dir];
        player.wy += DY[player.dir];
        player.step++;

        if (player.step >= player.len)
        {
            int tiles = player.len / TILE_PX;
            player.tx += DX[player.dir] * tiles;
            player.ty += DY[player.dir] * tiles;
            player.wx = player.tx * TILE_PX;
            player.wy = player.ty * TILE_PX;
            player.moving = false;
            if (!player.hop) player.phase ^= 1;
            player.hop  = false;
            player.step = 0;
        }
    }
}

// Altura del salto (arco de 0 a 8 px y de vuelta a 0)
static int hop_height()
{
    if (!player.hop) return 0;
    return player.step * (player.len - player.step) / player.len;
}

static int player_frame()
{
    int col = 1;
    if (player.moving && !player.hop && player.step < 8)
        col = player.phase ? 2 : 0;

    return (int)player.dir * 3 + col;
}

//---------------------------------------------------------------------------------
// main
//---------------------------------------------------------------------------------
int main()
{
    irq_init(NULL);
    irq_enable(II_VBLANK);

    init_video();
    init_player();

    // Primera carga del fondo con la pantalla apagada
    update_rows(player.wy + 8 - SCREEN_HEIGHT / 2);

    REG_DISPCNT = DCNT_MODE0 | DCNT_BG0 | DCNT_BG1 | DCNT_OBJ | DCNT_OBJ_1D;

    while (1)
    {
        key_poll();
        update_player();

        // Cámara siempre centrada en el jugador (en los bordes se ve el vacío)
        int camX = player.wx + 8 - SCREEN_WIDTH  / 2;
        int camY = player.wy + 8 - SCREEN_HEIGHT / 2;

        VBlankIntrWait();

        update_rows(camY);
        REG_BG0HOFS = camX & 511;  REG_BG0VOFS = camY & 511;
        REG_BG1HOFS = camX & 511;  REG_BG1VOFS = camY & 511;

        obj_set_pos(playerObj, player.wx - camX, player.wy - 16 - camY - hop_height());
        playerObj->attr2 = ATTR2_BUILD(player_frame() * PLAYER_FRAME_TILES, 0, 0);
    }

    return 0;
}