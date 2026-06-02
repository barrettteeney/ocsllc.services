/* Ambient hero background video controller.
   Activates any .hero-photo that contains a <video class="ambient-hero-video">.
   No-ops safely on pages without one. Muted, looping, lazy, battery-friendly. */
(function () {
  function init() {
    var heroes = document.querySelectorAll('.hero-photo');
    Array.prototype.forEach.call(heroes, function (hero) {
      var v = hero.querySelector('.ambient-hero-video');
      if (!v) return;
      hero.classList.add('has-ambient');

      var reduce = window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (reduce) return;                     // CSS hides the clip; photo + scrim remain

      v.muted = true; v.defaultMuted = true;
      v.loop = true; v.playsInline = true;
      v.setAttribute('muted', ''); v.setAttribute('playsinline', '');
      v.preload = 'auto';

      function play() { var p = v.play(); if (p && p.catch) p.catch(function () {}); }
      function reveal() { hero.classList.add('ambient-ready'); play(); }

      if (v.readyState >= 2) reveal();
      else v.addEventListener('loadeddata', reveal, { once: true });

      // pause when the hero is fully off-screen; resume when it returns
      if ('IntersectionObserver' in window) {
        new IntersectionObserver(function (entries) {
          entries.forEach(function (e) { e.isIntersecting ? play() : v.pause(); });
        }, { threshold: 0 }).observe(hero);
      }
      // resume after returning to the tab
      document.addEventListener('visibilitychange', function () {
        if (!document.hidden) play();
      });
    });
  }
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', init);
  else init();
})();
