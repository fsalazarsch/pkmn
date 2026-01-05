#include "SoundManager.h"
#include "sound_assets.h"
#include <cstdio>


int main() {
    SoundManager& sound = SoundManager::getInstance();

    sound.init();
    sound.startTrack(NEW_BARK_TOWN_THEME);
    while (true) {
        sound.update();
        
    }
    
    return 0;
}