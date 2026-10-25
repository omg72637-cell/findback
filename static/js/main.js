/**
 * FindBack 2.0 - Client-Side Enhancement & Safety Hints
 * Pure vanilla JavaScript with zero external libraries.
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Prohibited Credential Warning on Electronics Form
  var cluesTextarea = document.getElementById("distinctive_clues");
  var clueWarningBox = document.getElementById("credential_warning_hint");

  if (cluesTextarea && clueWarningBox) {
    var prohibitedPatterns = /\b(pin|password|passcode|recovery code|unlock pattern)\b/i;
    cluesTextarea.addEventListener("input", function () {
      if (prohibitedPatterns.test(cluesTextarea.value)) {
        clueWarningBox.style.display = "block";
      } else {
        clueWarningBox.style.display = "none";
      }
    });
  }

  // 2. Prevent Double Submissions on Forms
  var forms = document.querySelectorAll("form");
  forms.forEach(function (form) {
    form.addEventListener("submit", function () {
      var submitBtn = form.querySelector("button[type='submit']");
      if (submitBtn && !submitBtn.disabled) {
        // Delay slightly so form data is included in the submit event
        setTimeout(function () {
          submitBtn.disabled = true;
          submitBtn.innerText = "Processing...";
        }, 50);
      }
    });
  });
});
