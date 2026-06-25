document.addEventListener("DOMContentLoaded", function () {
  // Minimum date for date inputs
  const todayInputs = document.querySelectorAll("input[type='date']");
  const today = new Date().toISOString().split("T")[0];
  todayInputs.forEach((input) => {
    if (!input.min) input.min = today;
  });

  // Sticky header scroll state
  const header = document.getElementById("siteHeader");
  if (header) {
    const onScroll = () => header.classList.toggle("is-scrolled", window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  // Auto-dismiss flash alerts
  document.querySelectorAll(".mz-alert.alert-dismissible").forEach((alert) => {
    setTimeout(() => {
      alert.style.transition = "opacity 0.4s ease, transform 0.4s ease";
      alert.style.opacity = "0";
      alert.style.transform = "translateY(-6px)";
      setTimeout(() => alert.remove(), 400);
    }, 4500);
  });

  // Stagger product card entrance
  document.querySelectorAll(".product-card").forEach((card, i) => {
    card.style.animation = `fadeInUp 0.45s ${Math.min(i * 0.06, 0.4)}s ease both`;
  });
});
