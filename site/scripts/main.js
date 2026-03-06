(function () {
    // Sekcja pobierania elementów
    const sendBtn = document.getElementById("send");
    const syllEl = document.getElementById("syll");
    const typeEl = document.getElementById("type");
    const resultEl = document.getElementById("result");
    const spinner = document.getElementById("spinner");
    const statusText = document.getElementById("status-text");

    // Sekcja logiki zapytania
    let cooldown = false;

    sendBtn.addEventListener("click", async () => {
        if (cooldown) {
            statusEl.textContent = "Odczekaj 3 sekundy między zapytaniami.";
            return;
        }

        const syll = encodeURIComponent(syllEl.value);
        const type = encodeURIComponent(typeEl.value);

        spinner.classList.remove("hidden");
        let elapsed = 0;
        statusText.textContent = " Przetwarzanie... 0.0s";
        const timer = setInterval(() => {
            elapsed += 100;
            statusText.textContent = ` Przetwarzanie... ${(elapsed / 1000).toFixed(1)}s`;
        }, 100);

        sendBtn.disabled = true;
        cooldown = true;

        try {
            const res = await fetch("/dologic", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ syll, type }),
            });

            clearInterval(timer);
            spinner.classList.add("hidden");

            if (res.status === 429) {
                statusEl.textContent = "Ograniczenie przepustowości - poczekaj 3 sekundy.";
            } else if (res.ok) {
                const data = await res.json();
                resultEl.value = data.result;
                statusText.textContent = `Czas: ${(elapsed / 1000).toFixed(1)}s`;
            } else {
                statusText.textContent = "Error: " + res.statusText;
            }
        } catch (err) {
            clearInterval(timer);
            spinner.classList.add("hidden");
            statusEl.textContent = "Network error.";
        }

        setTimeout(() => {
            cooldown = false;
            sendBtn.disabled = false;
        }, 3000);
    });
})();