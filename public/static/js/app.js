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

  // Close mobile nav after tapping a link
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
});
