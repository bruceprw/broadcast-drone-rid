#include <zephyr/types.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
#include <zephyr.h>
#include <device.h>
#include <drivers/gpio.h>

#include <bluetooth/bluetooth.h>
#include <bluetooth/hci.h>
#include <bluetooth/conn.h>
#include <bluetooth/uuid.h>
#include <bluetooth/gatt.h>
#include <settings/settings.h>

#include <services/custom_service.h>

// GPIO for the buttons

// Button 1
#define SW0_NODE	DT_ALIAS(sw0)
#if !DT_NODE_HAS_STATUS(SW0_NODE, okay)
#error "Unsupported board: sw0 devicetree alias is not defined"
#endif
static const struct gpio_dt_spec button1 = GPIO_DT_SPEC_GET_OR(SW0_NODE, gpios,
							      {0});

#ifndef SW0_GPIO_FLAGS
#ifdef SW0_GPIO_PIN_PUD
#define SW0_GPIO_FLAGS SW0_GPIO_PIN_PUD
#else
#define SW0_GPIO_FLAGS 0
#endif
#endif

// Button 2
#define SW1_NODE	DT_ALIAS(sw1)
#if !DT_NODE_HAS_STATUS(SW1_NODE, okay)
#error "Unsupported board: sw1 devicetree alias is not defined"
#endif
static const struct gpio_dt_spec button2 = GPIO_DT_SPEC_GET_OR(SW1_NODE, gpios,
							      {0});

#ifndef SW1_GPIO_FLAGS
#ifdef SW1_GPIO_PIN_PUD
#define SW1_GPIO_FLAGS SW1_GPIO_PIN_PUD
#else
#define SW1_GPIO_FLAGS 0
#endif
#endif

static struct gpio_callback gpio_btnA_cb;
static struct gpio_callback gpio_btnB_cb;
static struct k_work buttonA_work;
static struct k_work buttonB_work;

#define DEVICE_NAME CONFIG_BT_DEVICE_NAME
#define DEVICE_NAME_LEN (sizeof(DEVICE_NAME) - 1)

bool authenticating = false;

struct bt_conn *default_conn;

static const struct bt_data ad[] = {
		BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
		BT_DATA(BT_DATA_NAME_COMPLETE, DEVICE_NAME, DEVICE_NAME_LEN),
};

// TODO implement pairing_passkey_display

// TODO implement auth_confirm

// TODO implement auth_cancel

// TODO specify callbacks for pairing - IO Capabilities are implied from this struct

static void connected(struct bt_conn *conn, uint8_t err)
{
	if (err)
	{
	}
	else
	{
		printk("Connected\n");
		default_conn = bt_conn_ref(conn);

		// TO DO request mode 1 level 4 security
	}
}

static void disconnected(struct bt_conn *conn, uint8_t reason)
{
	if (default_conn)
	{
		bt_conn_unref(default_conn);
		default_conn = NULL;
	}
}

// TODO implement security_level_changed

// TODO specify callback for security level changing
static struct bt_conn_cb conn_callbacks = {
		.connected = connected,
		.disconnected = disconnected,
};

static void bt_ready(int err)
{
	if (err)
	{
		return;
	}

	custom_service_init();

	if (IS_ENABLED(CONFIG_SETTINGS))
	{
		settings_load();
	}

	err = bt_le_adv_start(BT_LE_ADV_CONN, ad, ARRAY_SIZE(ad), NULL, 0);
	if (err)
	{
		return;
	}
}
void buttonA_work_handler(struct k_work *work)
{
	if (!authenticating)
	{
		return;
	}
	printk("User indicated YES\n");
	bt_conn_auth_passkey_confirm(default_conn);
	authenticating = false;
}

void buttonB_work_handler(struct k_work *work)
{
	if (!authenticating)
	{
		return;
	}
	printk("User indicated NO\n");
	bt_conn_auth_cancel(default_conn);
	authenticating = false;
}

void button_A_pressed(const struct device *gpiob, struct gpio_callback *cb,
											uint32_t pins)
{
	printk("Button A pressed\n");
	if (!authenticating)
	{
		return;
	}
	k_work_submit(&buttonA_work);
}

void button_B_pressed(const struct device *gpiob, struct gpio_callback *cb,
											uint32_t pins)
{
	printk("Button B pressed\n");
	k_work_submit(&buttonB_work);
}

void configureButtons(void)
{
	int ret;

	// Button 1
	k_work_init(&buttonA_work, buttonA_work_handler);
	ret = gpio_pin_configure_dt(&button1, GPIO_INPUT);
	if (ret != 0) {
		printk("Error %d: failed to configure %s pin %d\n",
		       ret, button1.port->name, button1.pin);
		return;
	}

	ret = gpio_pin_interrupt_configure_dt(&button1,
					      GPIO_INT_EDGE_TO_ACTIVE);
	if (ret != 0) {
		printk("Error %d: failed to configure interrupt on %s pin %d\n",
			ret, button1.port->name, button1.pin);
		return;
	}

	gpio_init_callback(&gpio_btnA_cb, button_A_pressed, BIT(button1.pin));
	gpio_add_callback(button1.port, &gpio_btnA_cb);
	printk("Set up button at %s pin %d\n", button1.port->name, button1.pin);

	// Button 2
	k_work_init(&buttonB_work, buttonB_work_handler);
	ret = gpio_pin_configure_dt(&button2, GPIO_INPUT);
	if (ret != 0) {
		printk("Error %d: failed to configure %s pin %d\n",
		       ret, button2.port->name, button2.pin);
		return;
	}

	ret = gpio_pin_interrupt_configure_dt(&button2,
					      GPIO_INT_EDGE_TO_ACTIVE);
	if (ret != 0) {
		printk("Error %d: failed to configure interrupt on %s pin %d\n",
			ret, button2.port->name, button2.pin);
		return;
	}

	gpio_init_callback(&gpio_btnB_cb, button_B_pressed, BIT(button2.pin));
	gpio_add_callback(button2.port, &gpio_btnB_cb);
	printk("Set up button at %s pin %d\n", button2.port->name, button2.pin);
}

void clear_all_bonds()
{

	printk("clearing all bonds\n");
	int rc = bt_unpair(BT_ID_DEFAULT, BT_ADDR_LE_ANY);
	printk("done [%d]\n", rc);
}

void main(void)
{

	printk("starting NCLEC\n");
	int err;
	configureButtons();
	err = bt_enable(bt_ready);
	if (err)
	{
		return;
	}

	clear_all_bonds();

	bt_conn_cb_register(&conn_callbacks);

    // TODO register callback for authentication step
}
