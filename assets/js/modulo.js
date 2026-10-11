// Comportamenti comuni delle pagine modulo
(function () {
  // istogrammi calcolati dal vivo
  document.querySelectorAll('img[data-histo]').forEach(function (img) {
    var cv = img.nextElementSibling;
    if (!cv || cv.tagName !== 'CANVAS' || !window.drawHistoFromImage) return;
    var go = function () { window.drawHistoFromImage(img, cv, getComputedStyle(document.documentElement).getPropertyValue('--glacier').trim()); };
    img.complete ? go() : img.addEventListener('load', go);
  });

  // lezione attiva nell'indice
  var links = [].slice.call(document.querySelectorAll('.toc ol a'));
  if ('IntersectionObserver' in window && links.length) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (e.isIntersecting) links.forEach(function (a) { a.classList.toggle('active', a.hash === '#' + e.target.id); });
      });
    }, { rootMargin: '-30% 0px -60% 0px' });
    document.querySelectorAll('article section[id]').forEach(function (s) { io.observe(s); });
  }

  // barra trasparente sulla foto di testata, materiale quando si scorre
  var bar = document.querySelector('.bar');
  if (bar) {
    var onScroll = function () { bar.classList.toggle('over-hero', scrollY < innerHeight * 0.55); };
    addEventListener('scroll', onScroll, { passive: true }); onScroll();
  }
})();
