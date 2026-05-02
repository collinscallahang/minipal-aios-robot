body_length = 100;
body_width = 90;
body_height = 70;
wall = 3;
corner_r = 10;

sensor_window = [34, 4, 18];
usb_window = [12, 16, 10];

module rounded_box(x, y, z, r) {
    hull() {
        translate([r, r, 0]) cylinder(h = z, r = r, $fn = 36);
        translate([x - r, r, 0]) cylinder(h = z, r = r, $fn = 36);
        translate([r, y - r, 0]) cylinder(h = z, r = r, $fn = 36);
        translate([x - r, y - r, 0]) cylinder(h = z, r = r, $fn = 36);
    }
}

module shell_body() {
    difference() {
        rounded_box(body_length, body_width, body_height, corner_r);

        translate([wall, wall, wall])
            rounded_box(
                body_length - 2 * wall,
                body_width - 2 * wall,
                body_height - wall,
                corner_r - 3
            );

        translate([
            body_length / 2 - sensor_window[0] / 2,
            -1,
            28
        ]) cube(sensor_window);

        translate([
            body_length - wall - 1,
            body_width / 2 - usb_window[1] / 2,
            16
        ]) cube(usb_window);

        translate([body_length / 2, body_width / 2, body_height - 1])
            cylinder(h = 4, d = 12, $fn = 36);
    }
}

module servo_platform() {
    translate([32, 31, 40]) cube([36, 28, 4]);
    translate([32, 31, 24]) cube([4, 28, 16]);
    translate([64, 31, 24]) cube([4, 28, 16]);
}

module pcb_standoffs() {
    for (p = [[24, 22], [76, 22], [24, 68], [76, 68]]) {
        translate([p[0], p[1], 6])
            difference() {
                cylinder(h = 8, d = 8, $fn = 24);
                cylinder(h = 8, d = 3, $fn = 24);
            }
    }
}

module battery_tray() {
    translate([20, 25, 3]) cube([60, 40, 4]);
}

shell_body();
servo_platform();
pcb_standoffs();
battery_tray();
