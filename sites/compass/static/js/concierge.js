(() => {
  const page = document.querySelector('#concierge-page');
  if (!page) return;
  const slides = [...page.querySelectorAll('.slide')];
  let current = 0;
  const show = (index) => {
    current = (index + slides.length) % slides.length;
    slides.forEach((slide, i) => {
      slide.hidden = i !== current;
      slide.classList.toggle('slide-active', i === current);
    });
    page.querySelector('[data-story-status]').textContent = `Success story ${current + 1} of ${slides.length}`;
  };
  page.querySelector('.slider-prev').addEventListener('click', () => show(current - 1));
  page.querySelector('.slider-next').addEventListener('click', () => show(current + 1));
  const chapters = page.querySelector('.concierge-chapters');
  const hero = page.querySelector('#hero');
  new IntersectionObserver(([entry]) => {
    chapters.classList.toggle('is-visible', !entry.isIntersecting);
    document.body.classList.toggle('concierge-reading', !entry.isIntersecting);
  }).observe(hero);
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
    page.querySelector('video').pause();
  }
})();
