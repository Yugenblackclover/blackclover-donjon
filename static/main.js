// Particles de trèfle
(function createParticles() {
    const container = document.getElementById('particles');
    if (!container) return;

    for (let i = 0; i < 18; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        p.style.left = Math.random() * 100 + '%';
        p.style.animationDuration = (10 + Math.random() * 14) + 's';
        p.style.animationDelay = (Math.random() * 12) + 's';
        p.style.width = (8 + Math.random() * 10) + 'px';
        p.style.height = p.style.width;
        p.style.opacity = 0.08 + Math.random() * 0.12;
        container.appendChild(p);
    }
})();

// Musique (optionnelle)
(function musicControl() {
    const audio = document.getElementById('bgm');
    const btn = document.getElementById('music-toggle');
    if (!audio || !btn) return;

    // Volume doux
    audio.volume = 0.25;

    btn.addEventListener('click', () => {
        if (audio.paused) {
            audio.play().then(() => {
                btn.classList.add('playing');
                btn.textContent = '🔊';
            }).catch(() => {
                // Pas de fichier musique → on ignore
                btn.title = "Ajoute un fichier static/music.mp3 pour la musique";
            });
        } else {
            audio.pause();
            btn.classList.remove('playing');
            btn.textContent = '🎵';
        }
    });
})();
