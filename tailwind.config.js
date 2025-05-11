module.exports = {
    content: ["./apps/**/*.{html,js}", "./templates/**/*.{html,js}", "./static/js/**/*.js"],
    theme: { extend: {} },
    plugins: [require("daisyui").default],
};