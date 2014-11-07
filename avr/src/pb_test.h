/*
 * pb_test.h: plipbox test mode
 *
 * Written by
 *  Christian Vogelgsang <chris@vogelgsang.org>
 *
 * This file is part of plipbox.
 * See README for copyright notice.
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
 *  02111-1307  USA.
 *
 */

#ifndef PB_TEST_H
#define PB_TEST_H

#include "global.h"

#define PB_TEST_IDLE	0
#define PB_TEST_OK      1
#define PB_TEST_ERROR   2

extern void pb_test_toggle_mode(void);
extern void pb_test_toggle_auto(void);
extern void pb_test_send_packet(u08 silent);

extern u08  pb_test_state(u08 eth_state, u08 pb_state);
extern u08  pb_test_worker(void);

#endif