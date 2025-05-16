module.exports = {
    content: ["./apps/**/*.{html,js}", "./templates/**/*.{html,js}", "./static/js/**/*.js"],
    theme: {
        extend: {
            colors: {
                "matching-holistic": "#0ea5e9", // Sky-500
                "matching-skills": "#22c55e", // Emerald-500
                "matching-experience": "#f97316", // Orange-500
                "matching-qualifications": "#a855f7", // Violet-500
                "matching-wildcard": "#f43f5e", // Rose-500
            },
        },
    },
    plugins: [require("daisyui").default],
};