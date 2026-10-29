document.documentElement.classList.add('js');
const toggle = document.querySelector('.nav-toggle');
const nav = document.querySelector('.nav');
if (toggle && nav) {
  const services = nav.querySelector('.service-nav');
  const closeServices = () => services?.removeAttribute('open');
  const close = () => {
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Open navigation');
    nav.classList.remove('is-open');
    closeServices();
  };
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    nav.classList.toggle('is-open', open);
    if (!open) closeServices();
  });
  nav.addEventListener('click', (event) => { if (event.target.closest('a')) close(); });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    if (services?.open) {
      closeServices();
      services.querySelector('summary')?.focus();
    } else if (toggle.getAttribute('aria-expanded') === 'true') {
      close();
      toggle.focus();
    }
  });
  document.addEventListener('click', (event) => {
    if (!nav.contains(event.target) && !toggle.contains(event.target)) close();
  });
  window.matchMedia('(min-width: 801px)').addEventListener('change', close);
}

// The original list remains a normal scrollable row without this enhancement.
const clients = document.querySelector('#clients');
if (clients) {
  const viewport = clients.querySelector('.clients-viewport');
  const track = clients.querySelector('.clients-track');
  const list = clients.querySelector('.client-list');
  const control = clients.querySelector('.clients-toggle');
  const label = clients.querySelector('.clients-toggle-label');
  if (viewport && track && list && control && label) {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const copy = list.cloneNode(true);
    copy.classList.add('client-list-copy');
    copy.setAttribute('aria-hidden', 'true');
    copy.setAttribute('inert', '');
    copy.removeAttribute('id');
    copy.querySelectorAll('[id]').forEach((element) => element.removeAttribute('id'));
    copy.querySelectorAll('img').forEach((image) => { image.alt = ''; image.draggable = false; });
    list.querySelectorAll('img').forEach((image) => { image.draggable = false; });

    let manualPause = false;
    let hovering = false;
    let focused = viewport.contains(document.activeElement);
    let visible = !('IntersectionObserver' in window);
    let cycleWidth = 0;
    let viewportWidth = 0;
    let frame = 0;
    let previousTime = 0;
    let position = viewport.scrollLeft;

    const canRun = () => !reducedMotion.matches && !manualPause && !hovering
      && !focused && visible && !document.hidden && cycleWidth > viewportWidth + 1;

    const stop = () => {
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
      previousTime = 0;
      clients.classList.remove('is-running');
    };

    const advance = (time) => {
      frame = 0;
      if (!canRun()) { stop(); return; }
      if (previousTime) {
        const seconds = Math.min((time - previousTime) / 1000, 0.1);
        position = (position + seconds * 32) % cycleWidth;
        viewport.scrollLeft = position;
      }
      previousTime = time;
      frame = requestAnimationFrame(advance);
    };

    const sync = () => {
      control.hidden = reducedMotion.matches;
      clients.classList.toggle('is-paused', manualPause || reducedMotion.matches);
      label.textContent = manualPause ? 'Play' : 'Pause';
      control.setAttribute('aria-label', manualPause ? 'Play client logos' : 'Pause client logos');
      if (canRun()) {
        if (!frame) {
          position = viewport.scrollLeft % cycleWidth;
          previousTime = 0;
          clients.classList.add('is-running');
          frame = requestAnimationFrame(advance);
        }
      } else stop();
    };

    const measure = () => {
      cycleWidth = list.getBoundingClientRect().width;
      viewportWidth = viewport.clientWidth;
      if (cycleWidth && viewport.scrollLeft >= cycleWidth) {
        viewport.scrollLeft %= cycleWidth;
      }
      position = viewport.scrollLeft;
      sync();
    };

    const applyMotionPreference = () => {
      stop();
      const current = cycleWidth ? viewport.scrollLeft % cycleWidth : viewport.scrollLeft;
      if (reducedMotion.matches) copy.remove();
      else if (!copy.isConnected) track.append(copy);
      viewport.scrollLeft = current;
      measure();
    };

    control.addEventListener('click', () => { manualPause = !manualPause; sync(); });
    viewport.addEventListener('pointerenter', (event) => {
      if (event.pointerType === 'touch') return;
      hovering = true;
      sync();
    });
    viewport.addEventListener('pointerleave', (event) => {
      if (event.pointerType === 'touch') return;
      hovering = false;
      sync();
    });
    viewport.addEventListener('focusin', () => { focused = true; sync(); });
    viewport.addEventListener('focusout', (event) => {
      focused = viewport.contains(event.relatedTarget);
      sync();
    });
    const pauseForBrowsing = () => { manualPause = true; sync(); };
    viewport.addEventListener('pointerdown', pauseForBrowsing, { passive: true });
    viewport.addEventListener('wheel', (event) => {
      if (Math.abs(event.deltaX) > 0.5 || event.shiftKey) pauseForBrowsing();
    }, { passive: true });
    viewport.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') pauseForBrowsing();
    });
    document.addEventListener('visibilitychange', sync);
    reducedMotion.addEventListener('change', applyMotionPreference);

    if ('IntersectionObserver' in window) {
      new IntersectionObserver((entries) => {
        visible = entries[0].isIntersecting;
        sync();
      }).observe(clients);
    }
    if ('ResizeObserver' in window) {
      const observer = new ResizeObserver(measure);
      observer.observe(viewport);
      observer.observe(list);
    } else window.addEventListener('resize', measure);
    applyMotionPreference();
  }
}
