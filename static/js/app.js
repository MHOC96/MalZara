document.addEventListener("DOMContentLoaded", function () {
  const todayInputs = document.querySelectorAll("input[type='date']");
  const today = new Date().toISOString().split("T")[0];
  todayInputs.forEach((input) => {
    if (!input.min) input.min = today;
  });

  const header = document.getElementById("siteHeader");
  if (header) {
    let ticking = false;
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        header.classList.toggle("is-scrolled", window.scrollY > 12);
        ticking = false;
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  document.querySelectorAll(".mz-alert.alert-dismissible").forEach((alert) => {
    setTimeout(() => {
      alert.style.transition = "opacity 0.4s ease, transform 0.4s ease";
      alert.style.opacity = "0";
      alert.style.transform = "translateY(-6px)";
      setTimeout(() => alert.remove(), 400);
    }, 4500);
  });

  const navCollapse = document.getElementById("navbarNav");
  if (navCollapse) {
    navCollapse.querySelectorAll(".nav-link, .btn").forEach((el) => {
      el.addEventListener("click", () => {
        if (window.innerWidth < 992 && navCollapse.classList.contains("show")) {
          const toggler = document.querySelector(".mz-toggler");
          toggler?.click();
        }
      });
    });
  }

  initTableScroll();
});

function initTableScroll() {
  document.querySelectorAll(".table-responsive").forEach((tableWrap) => {
    const panel = tableWrap.closest(".table-scroll-panel") || tableWrap.parentElement;
    const hint = panel?.querySelector(".swipe-hint");

    const update = () => {
      const scrollable = tableWrap.scrollWidth > tableWrap.clientWidth + 2;
      if (hint) {
        hint.style.display = scrollable ? "block" : "none";
        hint.classList.toggle("is-hidden", tableWrap.scrollLeft > 12);
      }
      tableWrap.classList.toggle("is-scrollable", scrollable);
      tableWrap.classList.toggle("is-at-start", tableWrap.scrollLeft <= 4);
    };

    tableWrap.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update, { passive: true });
    window.addEventListener("load", update);
    update();
    setTimeout(update, 150);
  });
}
