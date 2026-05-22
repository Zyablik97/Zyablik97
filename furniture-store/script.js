/* ============================================================
   PASTELLA — клиентский JS
   Loader · cursor · scroll · reveal · parallax · marquee · фильтры
   carousel · counters · forms · mobile menu · back-to-top
   ============================================================ */

(() => {
  'use strict';

  const $  = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => [...c.querySelectorAll(s)];
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- LOADER ---------- */
  window.addEventListener('load', () => {
    requestAnimationFrame(() => {
      setTimeout(() => {
        const loader = $('#loader');
        loader?.classList.add('is-hidden');
        document.body.classList.add('is-loaded');
        // remove loader from a11y tree after fade
        setTimeout(() => loader?.remove(), 900);
      }, 700);
    });
  });

  /* ---------- CUSTOM CURSOR ---------- */
  (() => {
    const cursor = $('#cursor');
    const dot    = $('#cursorDot');
    if (!cursor || !dot) return;
    // disable on touch devices
    if (window.matchMedia('(hover: none)').matches) {
      cursor.remove(); dot.remove(); return;
    }

    let mx = window.innerWidth / 2, my = window.innerHeight / 2;
    let cx = mx, cy = my;
    let visible = false;

    window.addEventListener('mousemove', (e) => {
      mx = e.clientX; my = e.clientY;
      dot.style.transform = `translate(${mx}px, ${my}px) translate(-50%, -50%)`;
      if (!visible) {
        cursor.classList.add('is-visible');
        dot.classList.add('is-visible');
        visible = true;
      }
    }, { passive: true });

    window.addEventListener('mouseout', (e) => {
      if (!e.relatedTarget) {
        cursor.classList.remove('is-visible');
        dot.classList.remove('is-visible');
        visible = false;
      }
    });

    const animate = () => {
      cx += (mx - cx) * 0.18;
      cy += (my - cy) * 0.18;
      cursor.style.transform = `translate(${cx}px, ${cy}px) translate(-50%, -50%)`;
      requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);

    // hover grow
    document.addEventListener('mouseover', (e) => {
      const el = e.target.closest('[data-cursor="grow"], a, button');
      if (el) cursor.classList.add('is-grow');
    });
    document.addEventListener('mouseout', (e) => {
      const el = e.target.closest('[data-cursor="grow"], a, button');
      if (el) cursor.classList.remove('is-grow');
    });
  })();

  /* ---------- HEADER ON SCROLL ---------- */
  (() => {
    const header = $('#header');
    if (!header) return;
    const onScroll = () => {
      header.classList.toggle('is-scrolled', window.scrollY > 30);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  })();

  /* ---------- MOBILE MENU ---------- */
  (() => {
    const burger = $('#burger');
    const nav    = $('#nav');
    if (!burger || !nav) return;

    const close = () => { burger.classList.remove('is-open'); nav.classList.remove('is-open'); document.body.style.overflow = ''; };
    const toggle = () => {
      const open = burger.classList.toggle('is-open');
      nav.classList.toggle('is-open', open);
      document.body.style.overflow = open ? 'hidden' : '';
    };

    burger.addEventListener('click', toggle);
    nav.addEventListener('click', (e) => { if (e.target.tagName === 'A') close(); });
    window.addEventListener('resize', () => { if (window.innerWidth > 860) close(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
  })();

  /* ---------- REVEAL ON SCROLL ---------- */
  (() => {
    const items = $$('.reveal');
    if (!items.length || prefersReducedMotion) {
      items.forEach(el => el.classList.add('is-visible'));
      return;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry, idx) => {
        if (entry.isIntersecting) {
          // stagger items inside same parent
          const peers = $$('.reveal', entry.target.parentElement);
          const peerIdx = peers.indexOf(entry.target);
          entry.target.style.transitionDelay = `${Math.min(peerIdx, 6) * 80}ms`;
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
    items.forEach(el => io.observe(el));
  })();

  /* ---------- PARALLAX ---------- */
  (() => {
    if (prefersReducedMotion) return;
    const layers = $$('[data-parallax]');
    if (!layers.length) return;

    let raf = 0;
    const update = () => {
      const sy = window.scrollY;
      for (const el of layers) {
        const speed = parseFloat(el.dataset.parallax) || 0.2;
        el.style.transform = `translate3d(0, ${sy * speed}px, 0)`;
      }
      raf = 0;
    };
    window.addEventListener('scroll', () => {
      if (!raf) raf = requestAnimationFrame(update);
    }, { passive: true });
    update();
  })();

  /* ---------- COUNTERS ---------- */
  (() => {
    const counters = $$('[data-counter]');
    if (!counters.length) return;
    const animate = (el) => {
      const target = parseInt(el.dataset.counter, 10) || 0;
      const suffix = el.dataset.suffix || '';
      const dur = 1600;
      const start = performance.now();
      const tick = (t) => {
        const p = Math.min((t - start) / dur, 1);
        const eased = 1 - Math.pow(1 - p, 3);
        const v = Math.round(target * eased);
        el.textContent = v.toLocaleString('ru-RU') + suffix;
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) { animate(e.target); io.unobserve(e.target); }
      });
    }, { threshold: 0.4 });
    counters.forEach(el => io.observe(el));
  })();

  /* ---------- FILTERS (catalog) ---------- */
  (() => {
    const chips = $$('.chip[data-filter]');
    const products = $$('#products .product');
    if (!chips.length || !products.length) return;

    chips.forEach((chip) => {
      chip.addEventListener('click', () => {
        chips.forEach(c => c.classList.remove('is-active'));
        chip.classList.add('is-active');
        const f = chip.dataset.filter;
        products.forEach((p) => {
          const show = f === 'all' || p.dataset.cat === f;
          p.classList.toggle('is-hidden', !show);
        });
      });
    });
  })();

  /* ---------- ADD-TO-CART micro-feedback ---------- */
  (() => {
    $$('.product__add').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        btn.classList.add('is-added');
        const original = btn.textContent;
        btn.textContent = '✓ Добавлено';
        setTimeout(() => {
          btn.classList.remove('is-added');
          btn.textContent = original;
        }, 1600);

        // bump bag badge
        const badge = $('.icon-btn__badge');
        if (badge) {
          const n = parseInt(badge.textContent, 10) || 0;
          badge.textContent = n + 1;
          badge.animate(
            [{ transform: 'scale(1)' }, { transform: 'scale(1.4)' }, { transform: 'scale(1)' }],
            { duration: 350, easing: 'cubic-bezier(.34,1.56,.64,1)' }
          );
        }
      });
    });
  })();

  /* ---------- REVIEWS CAROUSEL ---------- */
  (() => {
    const track = $('.reviews__track');
    const prev  = $('#reviewsPrev');
    const next  = $('#reviewsNext');
    const dotsBox = $('#reviewsDots');
    if (!track || !prev || !next || !dotsBox) return;

    const slides = $$('.review', track);
    let index = 0;
    let timer = 0;
    let perView = window.innerWidth <= 860 ? 1 : 2;
    let pages = Math.max(1, slides.length - (perView - 1));

    const buildDots = () => {
      dotsBox.innerHTML = '';
      for (let i = 0; i < pages; i++) {
        const d = document.createElement('i');
        d.addEventListener('click', () => goTo(i));
        dotsBox.appendChild(d);
      }
      updateDots();
    };

    const updateDots = () => {
      $$('.reviews__dots i').forEach((d, i) => d.classList.toggle('is-active', i === index));
    };

    const goTo = (i) => {
      index = (i + pages) % pages;
      const target = slides[index];
      if (target) {
        track.scrollTo({ left: target.offsetLeft - track.offsetLeft, behavior: 'smooth' });
      }
      updateDots();
    };

    const auto = () => { clearInterval(timer); timer = setInterval(() => goTo(index + 1), 5000); };
    const stop = () => clearInterval(timer);

    prev.addEventListener('click', () => { goTo(index - 1); auto(); });
    next.addEventListener('click', () => { goTo(index + 1); auto(); });
    track.addEventListener('mouseenter', stop);
    track.addEventListener('mouseleave', auto);

    // observe manual scrolling, update index
    track.addEventListener('scroll', () => {
      // find nearest slide
      let best = 0, bestDist = Infinity;
      const left = track.scrollLeft;
      slides.forEach((s, i) => {
        const d = Math.abs(s.offsetLeft - track.offsetLeft - left);
        if (d < bestDist) { bestDist = d; best = i; }
      });
      if (best !== index) { index = Math.min(best, pages - 1); updateDots(); }
    }, { passive: true });

    window.addEventListener('resize', () => {
      const newPerView = window.innerWidth <= 860 ? 1 : 2;
      if (newPerView !== perView) {
        perView = newPerView;
        pages = Math.max(1, slides.length - (perView - 1));
        index = 0;
        buildDots();
        goTo(0);
      }
    });

    buildDots();
    auto();
  })();

  /* ---------- NEWSLETTER FORM ---------- */
  (() => {
    const form = $('#newsletterForm');
    if (!form) return;
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = form.querySelector('input[type="email"]');
      const value = (input?.value || '').trim();
      const ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
      form.classList.remove('is-submitted', 'is-success');
      // restart animation by reflow
      void form.offsetWidth;
      form.classList.add('is-submitted');
      if (!ok) { input?.focus(); return; }
      form.classList.add('is-success');
      const btn = form.querySelector('button');
      const original = btn?.innerHTML;
      if (btn) btn.innerHTML = '<span>✓ Готово, проверьте почту</span>';
      setTimeout(() => { if (btn && original) btn.innerHTML = original; form.classList.remove('is-success', 'is-submitted'); }, 3000);
      input.value = '';
    });
  })();

  /* ---------- BACK TO TOP ---------- */
  (() => {
    const btn = $('#backToTop');
    if (!btn) return;
    const onScroll = () => btn.classList.toggle('is-visible', window.scrollY > 600);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  })();

  /* ---------- SMOOTH ANCHOR (extra offset for sticky header) ---------- */
  (() => {
    document.addEventListener('click', (e) => {
      const a = e.target.closest('a[href^="#"]');
      if (!a) return;
      const id = a.getAttribute('href');
      if (!id || id.length <= 1) return;
      const target = document.querySelector(id);
      if (!target) return;
      e.preventDefault();
      const offset = 70;
      const top = target.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    });
  })();

})();
