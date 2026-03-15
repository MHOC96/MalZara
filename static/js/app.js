document.addEventListener("DOMContentLoaded", function () {
  const todayInputs = document.querySelectorAll("input[type='date']");
  const today = new Date().toISOString().split("T")[0];

  todayInputs.forEach((input) => {
    if (!input.min) {
      input.min = today;
    }
  });
});
