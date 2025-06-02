// ==UserScript==
// @name         Redirect with Keyword from Localhost (Via Browser)
// @namespace    http://yourdomain.com/
// @version      1.1
// @description  Fetch keyword from local server and redirect to Google every 60s with countdown display
// @match        *://*/*
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  function getRandomDelay(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }

  const delaySeconds = getRandomDelay(7, 30);
  let countdown = delaySeconds;

  // Show countdown
  const timerBox = document.createElement("div");
  timerBox.style.position = "fixed";
  timerBox.style.bottom = "10px";
  timerBox.style.right = "10px";
  timerBox.style.background = "rgba(0,0,0,0.7)";
  timerBox.style.color = "white";
  timerBox.style.padding = "6px 12px";
  timerBox.style.borderRadius = "8px";
  timerBox.style.fontSize = "16px";
  timerBox.style.zIndex = 9999;
  timerBox.textContent = `Redirect in ${countdown}s`;
  document.body.appendChild(timerBox);

  const countdownInterval = setInterval(() => {
    countdown--;
    timerBox.textContent = `Redirect in ${countdown}s`;

    if (countdown <= 0) {
      clearInterval(countdownInterval);
      fetchAndRedirect();
    }
  }, 1000);

  async function fetchAndRedirect() {
    try {
      const response = await fetch("http://localhost:3000/keyword");
      if (!response.ok) throw new Error("Fetch failed");

      const data = await response.json();
      const keyword = data.keyword;

      if (keyword) {
        const url = `https://www.bing.com/search?q=${encodeURIComponent(
          keyword
        )}`;
        window.top.location.href = url;
      } else {
        timerBox.textContent = "âš ï¸ No keyword found";
      }
    } catch (e) {
      timerBox.textContent = "âš ï¸ Error: " + e.message;
    }
  }
})();
