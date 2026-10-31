/* Mobile menu: below lg the header sections fold into one button, which sits
   where the memory counter used to be. The panel closes on Escape, on a click
   outside it and after a link is chosen. */
(function mobileMenu() {
    const toggle = document.getElementById('menu-toggle');
    const menu = document.getElementById('mobile-menu');
    const backdrop = document.getElementById('mobile-menu-backdrop');
    if (!toggle || !menu || !backdrop) return;

    const openIcon = toggle.querySelector('.menu-icon-open');
    const closeIcon = toggle.querySelector('.menu-icon-close');
    const wide = window.matchMedia('(min-width: 1024px)');
    let open = false;

    const items = () => Array.from(menu.querySelectorAll('a[href], button'))
        .filter((el) => !el.disabled && el.getClientRects().length);

    function show() {
        if (open) return;
        open = true;
        menu.classList.remove('hidden');
        backdrop.classList.remove('hidden');
        toggle.setAttribute('aria-expanded', 'true');
        toggle.setAttribute('aria-label', 'Chiudi il menu');
        openIcon?.classList.add('hidden');
        closeIcon?.classList.remove('hidden');
        items()[0]?.focus({ preventScroll: true });
    }

    function hide(restoreFocus = true) {
        if (!open) return;
        open = false;
        menu.classList.add('hidden');
        backdrop.classList.add('hidden');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.setAttribute('aria-label', 'Apri il menu');
        openIcon?.classList.remove('hidden');
        closeIcon?.classList.add('hidden');
        if (restoreFocus) toggle.focus({ preventScroll: true });
    }

    toggle.addEventListener('click', () => (open ? hide() : show()));
    backdrop.addEventListener('click', () => hide());
    menu.addEventListener('click', (event) => {
        if (event.target.closest('a[href]')) hide(false);
    });

    // Capture, so Escape also beats the slideshow's own key handlers.
    document.addEventListener('keydown', (event) => {
        if (!open || event.key !== 'Escape') return;
        event.preventDefault();
        event.stopPropagation();
        hide();
    }, true);

    wide.addEventListener('change', (event) => { if (event.matches) hide(false); });

    // "Lascia un pensiero" is only offered when the Tally form is configured:
    // the header button is the single source of truth for that.
    const thoughts = document.getElementById('menu-thoughts');
    const headerThoughts = document.getElementById('leave-thought');
    if (thoughts) {
        if (headerThoughts && headerThoughts.classList.contains('hidden')) {
            thoughts.remove();
        } else {
            thoughts.classList.remove('hidden');
            thoughts.classList.add('flex');
            thoughts.addEventListener('click', () => {
                hide(false);
                if (window.fbThoughts) window.fbThoughts.open();
            });
        }
    }
})();
