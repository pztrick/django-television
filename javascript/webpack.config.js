var webpack = require('webpack');
var path = require('path');

var config = {
    entry: __dirname + '/src/index.js',
    devtool: 'source-map',
    output: {
        path: path.join(__dirname, 'dist'),
        filename: "[name].js",
        libraryTarget: "umd",
    },
    watch: true,
    module: {
        rules: [
            {
                test: /\.jsx?$/,
                loaders: ['babel-loader'],
                include: path.join(__dirname, 'src')
            },
            {
                test: /^((?!\.module).)*\.styl$/,
                loaders: [
                    'style-loader',
                    'css-loader',
                    'stylus-loader'
                ]
            },
        ],

    },
};

module.exports = config;