(() => {
  const stack = document.querySelector('[data-sell-stack]');
  if (!stack) return;
  const cards = [...stack.querySelectorAll('[data-stack-card]')];
  let selected = 0;
  function renderStack() {
    cards.forEach((card, index) => {
      const depth = (index - selected + cards.length) % cards.length;
      card.style.zIndex = String(cards.length - depth);
      card.style.transform = `translateX(var(--card-offset-x-${depth})) translateY(var(--card-offset-y-${depth}))`;
      const shade = depth === 1 ? 17 : 67;
      card.querySelector('.sell-card-shade').style.background = depth ? `rgba(${shade},${shade},${shade},${depth / 3})` : 'transparent';
      card.setAttribute('aria-hidden', String(depth !== 0));
    });
    stack.querySelector('[data-stack-status]').textContent = `${cards[selected].getAttribute('aria-label')}, ${selected + 1} of ${cards.length}`;
  }
  stack.querySelectorAll('[data-stack-step]').forEach(button => button.addEventListener('click', () => {
    selected = (selected + Number(button.dataset.stackStep) + cards.length) % cards.length;
    renderStack();
  }));
  cards.forEach((card, index) => card.addEventListener('click', () => { selected = index; renderStack(); }));
  renderStack();

  const carousel = document.querySelector('[data-sell-carousel]');
  const track = carousel.querySelector('[data-appearance-track]');
  const slides = [...carousel.querySelectorAll('[data-appearance-card]')];
  let slideIndex = 0;
  function renderSlide() {
    const offset = slides[slideIndex].offsetLeft - slides[0].offsetLeft;
    track.style.transform = `translate3d(${-offset}px,0,0)`;
    slides.forEach((slide, index) => slide.setAttribute('aria-hidden', String(index !== slideIndex)));
    carousel.querySelector('[data-appearance-status]').textContent = `Listing comparison ${slideIndex + 1} of ${slides.length}`;
  }
  carousel.querySelectorAll('[data-appearance-step]').forEach(button => button.addEventListener('click', () => {
    slideIndex = (slideIndex + Number(button.dataset.appearanceStep) + slides.length) % slides.length;
    renderSlide();
  }));
  new ResizeObserver(renderSlide).observe(track.parentElement);
  renderSlide();
})();
