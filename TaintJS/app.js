// filesystem require
var fs = require('fs');
var esprima = require('esprima');


if (process.argv.length < 3) {
    console.log('Usage: node ' + process.argv[1] + ' FILENAME');
    process.exit(-1);
}
// Read the file and print its contents.

// second argument cl
filename = process.argv[2];

fs.readFile(filename, 'utf-8', function read(err, data) {
    if (err) {
        throw err;
    }

    analyzeContent(data);
});

function analyzeContent(data) {
    // from here content file is available
    //console.log("Content file to analyze is :");
    //console.log(data);
    var options = {
        loc: true,
        comment: false,
        raw: false,
        range: false,
        tolerant: false
    };
    var engine = require('./engine.js');
    var analyzer = require('./analyzer.js');

    var result = esprima.parse(data, options);
    var str_result = JSON.stringify(result, null, 4);
//    console.log(str_result)
    engine.analyze(str_result);
    engine.asignFunctionReturnValue(analyzer.sink);
    isXss = analyzer.analyzeArrays(engine.real_func_names, engine.real_func_call, engine.real_variable_const, engine.real_variable_var, engine.real_variable_obj, engine.startScope, engine.endScope, data, null);
    console.log(isXss);
    if (isXss){
        process.exit(1)
    }else{
        process.exit(0)
    }

}