/* Scroll-reveal, matching the upstream landing page's opacity/transform
   transition. Content is visible without JS: elements only start hidden once
   this script has run, and anything already on screen is shown immediately. */
(function () {
  var nodes = document.querySelectorAll('.reveal-on-scroll');
  if (!nodes.length) return;
  if (!('IntersectionObserver' in window) ||
      window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    nodes.forEach(function (el) { el.classList.add('shown'); });
    return;
  }
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('shown');
      observer.unobserve(entry.target);
    });
  }, { rootMargin: '0px 0px -12% 0px', threshold: 0.08 });
  nodes.forEach(function (el) { observer.observe(el); });
})();
