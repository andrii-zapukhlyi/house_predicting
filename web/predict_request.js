async function predict() {
    const features = [
        parseFloat(document.getElementById("area").value),
        parseInt(document.getElementById("rooms").value),
        parseInt(document.getElementById("floor").value),
        parseFloat(document.getElementById("rent").value),
        document.querySelector('input[name="parking"]:checked').value === "true" ? 1 : 0,
        parseInt(document.getElementById("construction_year").value),
        document.querySelector('input[name="elevator"]:checked').value === "true" ? 1 : 0,
        document.getElementById("location").value,
        document.getElementById("voivodship").value,
        document.getElementById("outdoor_space").value,
        document.getElementById("heating").value,
        document.getElementById("building").value
    ];

    try {
        const response = await fetch("http://127.0.0.1:8000/predict/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ features: features })
        });

        const data = await response.json();
        document.getElementById("result").innerText = `Predicted Price: ${data} zł`;
    } catch (error) {
        console.error("Error:", error);
        document.getElementById("result").innerText = "Prediction failed. Check console for errors.";
    }
}