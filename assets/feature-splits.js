/* OCS LLC — feature-split rows: reveal on scroll, lazy-autoplay reels in view,
   tap a reel to toggle sound. Vanilla, reusable on any page. */
(function () {
  'use strict';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function play(v) { var p = v.play(); if (p && p.catch) p.catch(function () {}); }

  // Reveal each row as it scrolls in.
  var rows = Array.prototype.slice.call(document.querySelectorAll('.vsplit'));
  if (reduce || !('IntersectionObserver' in window)) {
    rows.forEach(function (r) { r.classList.add('in'); });
  } else {
    var ro = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); ro.unobserve(e.target); } });
    }, { threshold: 0.2, rootMargin: '0px 0px -8% 0px' });
    rows.forEach(function (r) { ro.observe(r); });
  }

  // Lazy muted-autoplay reels only while in view.
  var vids = Array.prototype.slice.call(document.querySelectorAll('video[data-vs]'));
  if (!reduce && 'IntersectionObserver' in window) {
    var vo = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        var v = e.target;
        if (e.isIntersecting) { if (v.preload === 'none') v.preload = 'auto'; play(v); }
        else v.pause();
      });
    }, { threshold: 0.35 });
    vids.forEach(function (v) { vo.observe(v); });
  } else {
    vids.forEach(function (v) { v.removeAttribute('autoplay'); });
  }

  // Tap a frame to toggle sound.
  document.querySelectorAll('.vframe').forEach(function (f) {
    f.addEventListener('click', function () {
      var v = f.querySelector('video');
      v.muted = !v.muted;
      f.classList.toggle('unmuted', !v.muted);
      if (!v.muted) play(v);
    });
  });
})();
