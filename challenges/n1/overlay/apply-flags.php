<?php
/**
 * Sustituye las banderas del laboratorio CTF UCC por las de entrenamiento preCTF.
 * Se ejecuta al arrancar el contenedor, con los valores de PRECTF_FLAG_N*.
 */

function prectf_env(string $name): string
{
    $value = getenv($name);
    return is_string($value) ? $value : '';
}

function prectf_replacements(): array
{
    $n1 = prectf_env('PRECTF_FLAG_N1');
    $n2 = prectf_env('PRECTF_FLAG_N2');
    $n3 = prectf_env('PRECTF_FLAG_N3');
    $n4 = prectf_env('PRECTF_FLAG_N4');
    $n5 = prectf_env('PRECTF_FLAG_N5');
    $n6 = prectf_env('PRECTF_FLAG_N6');
    $n7 = prectf_env('PRECTF_FLAG_N7');
    $n8 = prectf_env('PRECTF_FLAG_N8');

    return [
        'FLAG{UCC_Cookie_Bypass_OK}' => $n2,
        'FLAG{UCC_IDS_Cookie_Bypass}' => $n2,
        'FLAG{UCC_UWS_Cookie_Bypass}' => $n2,
        'FLAG{UCC_IDS_LFI_Found}' => $n3,
        'FLAG{UCC_UWS_LFI_Found}' => $n3,
        'FLAG{UCC_IDS_Config_Leaked}' => $n4,
        'FLAG{UCC_UWS_Config_Leaked}' => $n4,
        'FLAG{UCC_IDS_Hash_Cracked}' => $n6,
        'FLAG{UCC_UWS_Hash_Cracked}' => $n6,
        'FLAG{UCC_Ciber_Atrapada}' => $n8,
        'FLAG{UCC_UWS_Pwned}' => $n8,
        'FLAG{UCC_IDS_SQLi_Bypass}' => $n1,
        'FLAG{UCC_UWS_SQLi_Bypass}' => $n1,
        'FLAG{UCC_IDS_Cmd_Inject}' => $n5,
        'FLAG{UCC_UWS_Cmd_Inject}' => $n5,
        'FLAG{UCC_IDS_Upload_RCE}' => $n7,
        'FLAG{UCC_UWS_Upload_RCE}' => $n7,
    ];
}

function prectf_apply_file(string $template, string $dest, array $map): void
{
    if (!is_file($template)) {
        return;
    }
    $contents = file_get_contents($template);
    if ($contents === false) {
        return;
    }
    $updated = strtr($contents, $map);
    $dir = dirname($dest);
    if (!is_dir($dir)) {
        mkdir($dir, 0755, true);
    }
    file_put_contents($dest, $updated);
}

function prectf_apply_db(string $flagN6): void
{
    if ($flagN6 === '') {
        return;
    }
    $mysqli = @new mysqli('localhost', 'root', '', 'ctf_login', 3306, '/var/run/mysqld/mysqld.sock');
    if ($mysqli->connect_errno) {
        fwrite(STDERR, "prectf-flags: MariaDB no disponible ({$mysqli->connect_error})\n");
        return;
    }
    $mysqli->set_charset('utf8mb4');
    $hint = 'Cuando descifres los 3 hashes MD5, somete: ' . $flagN6;
    $stmt = $mysqli->prepare('UPDATE secrets SET value = ? WHERE label = ?');
    if ($stmt === false) {
        $mysqli->close();
        return;
    }
    $label = 'hash_flag_hint';
    $stmt->bind_param('ss', $hint, $label);
    $stmt->execute();
    $stmt->close();
    $mysqli->close();
}

function prectf_plant_n5(string $flag): void
{
    if ($flag === '' || str_contains($flag, ':')) {
        return;
    }
    $passwd = @file_get_contents('/etc/passwd');
    if ($passwd === false) {
        return;
    }
    $lines = [];
    foreach (explode("\n", $passwd) as $line) {
        if ($line === '' || str_starts_with($line, 'prectf_n5:')) {
            continue;
        }
        $lines[] = $line;
    }
    $lines[] = "prectf_n5:x:65533:65533:{$flag}:/nonexistent:/usr/sbin/nologin";
    file_put_contents('/etc/passwd', implode("\n", $lines) . "\n");
}

function prectf_plant_file(string $path, string $flag): void
{
    if ($flag === '') {
        return;
    }
    $dir = dirname($path);
    if (!is_dir($dir)) {
        mkdir($dir, 0755, true);
    }
    file_put_contents($path, $flag . "\n");
}

$map = prectf_replacements();
prectf_apply_file('/opt/prectf/templates/admin.php', '/var/www/html/admin.php', $map);
prectf_apply_file('/opt/prectf/templates/admin_notes.md', '/var/www/html/bucket/admin_notes.md', $map);
prectf_apply_file('/opt/prectf/templates/app.ini', '/var/www/html/config/app.ini', $map);
prectf_apply_db(prectf_env('PRECTF_FLAG_N6'));
prectf_plant_n5(prectf_env('PRECTF_FLAG_N5'));
prectf_plant_file('/opt/prectf/n7.flag', prectf_env('PRECTF_FLAG_N7'));
prectf_plant_file('/home/admin/flag.txt', prectf_env('PRECTF_FLAG_N8'));
