###########################################################
#
# transmission
#
###########################################################

TRANSMISSION_VERSION = 3.00
TRANSMISSION_SOURCE = transmission-$(TRANSMISSION_VERSION).tar.xz
TRANSMISSION_SITE = https://github.com/transmission/transmission/releases/download/3.00

TRANSMISSION_AUTORECONF = NO
TRANSMISSION_LIBTOOL_PATCH = NO

TRANSMISSION_DEPENDENCIES = uclibc libcurl openssl libevent2 pkg-config
TRANSMISSION_CONF_OPT = --disable-nls --enable-utp --enable-cli --enable-lightweight

$(eval $(call AUTOTARGETS,package,transmission))
