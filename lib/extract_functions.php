#!/usr/bin/env php
<?php

/**
 * That script makes use of the PHP-Parser library (https://github.com/nikic/PHP-Parser)
 * to extract all functions from a PHP file (whose absolute path is given as argument) and
 * return all the functions' names indexed by the line on which they are defined
 *
 * @package        ZomPHP
 */

// fetch the code
if (count($argv) != 2 || !is_string($path = $argv[1]) || !strlen($path) || $path[0] !== '/') {
    echo 'Usage: '.$argv[0].' /absolute/path/to_file.php'.PHP_EOL;
    exit(1);
}
if (!is_readable($path)) {
    echo $path.' does not exist or is not readable'.PHP_EOL;
    exit(1);
}
$code = file_get_contents($path);
if (!$code) {
    echo 'Could not read from '.$path.PHP_EOL;
    exit(1);
}

// let's load PHP-Parser's autoloader

require(dirname(__FILE__).'/vendor/PHP-Parser/lib/bootstrap.php');

// down to work
class ZomphpFunctionExtractor extends PHPParser_NodeVisitorAbstract
{
    private $zomphpFunctions = array();

    public function enterNode(PHPParser_Node $node) {
        if ($node instanceof PHPParser_Node_Stmt_Function || $node instanceof PHPParser_Node_Stmt_ClassMethod) {
            $this->addZomphpFunction($node->name, $node->getLine());
        } elseif ($node instanceof PHPParser_Node_Expr_Closure) {
            // ZomPHP expects that {closure} string for lambda functions
            $this->addZomphpFunction('{closure}', $node->getLine());
        }
    }

    private function addZomphpFunction($funcName, $lineNo) {
        if (!array_key_exists($lineNo, $this->zomphpFunctions)) {
            $this->zomphpFunctions[$lineNo] = array();
        }
        $this->zomphpFunctions[$lineNo][] = $funcName;
    }

    public function getZomphpFunctions() {
        return $this->zomphpFunctions;
    }
}

$parser        = new PHPParser_Parser(new PHPParser_Lexer);
$traverser     = new PHPParser_NodeTraverser;
$prettyPrinter = new PHPParser_PrettyPrinter_Default;
$extractor     = new ZomphpFunctionExtractor;
$traverser->addVisitor($extractor);

try {
    // parse...
    $stmts = $parser->parse($code);
    // ... and traverse
    $stmts = $traverser->traverse($stmts);
} catch (PHPParser_Error $e) {
    echo 'Parse Error: ', $e->getMessage().PHP_EOL;
    exit(1);
}

if ($result = $extractor->getZomphpFunctions()) {
    echo json_encode($result);
}
