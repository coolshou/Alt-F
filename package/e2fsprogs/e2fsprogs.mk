#############################################################
#
# e2fsprogs
#
#############################################################

#E2FSPROGS_VERSION:=1.41.14
E2FSPROGS_VERSION:=1.42.13
#E2FSPROGS_VERSION:=1.43.3 rootfs too big by 131136/53312 bytes (Alt-F-1.1)
#E2FSPROGS_VERSION:=1.44.2 rootfs too big by 69696/36928 bytes (Alt-F-1.1)

E2FSPROGS_SOURCE=e2fsprogs-$(E2FSPROGS_VERSION).tar.gz
E2FSPROGS_SITE=$(BR2_SOURCEFORGE_MIRROR)/project/e2fsprogs/e2fsprogs/v$(E2FSPROGS_VERSION)

E2FSPROGS_DIR=$(BUILD_DIR)/e2fsprogs-$(E2FSPROGS_VERSION)
E2FSPROGS_CAT:=$(ZCAT)
E2FSPROGS_BINARY:=misc/mke2fs
E2FSPROGS_TARGET_BINARY:=usr/sbin/mke2fs
LIBUUID_DIR=$(E2FSPROGS_DIR)/lib/uuid/
LIBUUID_TARGET_DIR:=usr/lib/
LIBUUID_TARGET_BINARY:=libuuid.so

E2FSPROGS_EXTRA_BIN= ./usr/lib/libss.so ./usr/lib/libss.so.2 ./usr/lib/libss.so.2.0 \
	./usr/sbin/dumpe2fs ./usr/sbin/filefrag ./usr/sbin/e2undo ./usr/sbin/e4crypt \
	./usr/sbin/uuidd ./usr/sbin/debugfs ./usr/sbin/e2image \
	./usr/sbin/e2freefrag ./usr/sbin/findfs ./usr/sbin/badblocks ./usr/sbin/logsave

E2FSPROGS_OPTS = --enable-elf-shlibs --enable-libuuid --enable-libblkid \
	--enable-symlink-install --enable-relative-symlinks \
	--disable-testio-debug --disable-backtrace \
	--enable-resizer --enable-fsck --disable-tls --disable-e2initrd-helper \
	--enable-uuidd --enable-debugfs --enable-imager --disable-defrag

# FIXME: 1.42.13 configure: WARNING: unrecognized options: --disable-bmap-stats, --disable-tdb, --disable-mmp, --disable-fuse2fs

#ifeq ($(BR2_PACKAGE_E2FSPROGS_EXTRA),y)
# FIXME: --enable-defrag (for > 1.41.14, fallocate64 missing in uclibc, see
# http://lists.uclibc.org/pipermail/uclibc-cvs/2014-September/031327.html and
# http://lists.busybox.net/pipermail/uclibc/2014-September/048607.html
#	E2FSPROGS_OPTS += 
#else
#	E2FSPROGS_OPTS += --disable-uuidd --disable-debugfs --disable-imager
#endif

$(DL_DIR)/$(E2FSPROGS_SOURCE):
	 $(call DOWNLOAD,$(E2FSPROGS_SITE),$(E2FSPROGS_SOURCE))

e2fsprogs-source: $(DL_DIR)/$(E2FSPROGS_SOURCE)

$(E2FSPROGS_DIR)/.unpacked: $(DL_DIR)/$(E2FSPROGS_SOURCE)
	$(E2FSPROGS_CAT) $(DL_DIR)/$(E2FSPROGS_SOURCE) | tar -C $(BUILD_DIR) $(TAR_OPTIONS) -
	toolchain/patch-kernel.sh $(E2FSPROGS_DIR) package/e2fsprogs/ e2fsprogs-$(E2FSPROGS_VERSION)\*.patch
	$(CONFIG_UPDATE) $(E2FSPROGS_DIR)/config
	touch $@

$(E2FSPROGS_DIR)/.configured: $(E2FSPROGS_DIR)/.unpacked
	(cd $(E2FSPROGS_DIR); rm -rf config.cache; \
		$(TARGET_CONFIGURE_OPTS) \
		$(TARGET_CONFIGURE_ARGS) \
		$(TARGET_CONFIGURE_ENV) \
		CFLAGS="$(TARGET_CFLAGS) $(BR2_PACKAGE_E2FSPROGS_OPTIM)" \
		./configure \
		--target=$(GNU_TARGET_NAME) \
		--host=$(GNU_TARGET_NAME) \
		--build=$(GNU_HOST_NAME) \
		--prefix=/usr \
		--exec-prefix=/usr \
		--bindir=/usr/bin \
		--sbindir=/usr/sbin \
		--libdir=/usr/lib \
		--libexecdir=/usr/lib \
		--sysconfdir=/etc \
		--datadir=/usr/share \
		--localstatedir=/var \
		--mandir=/usr/share/man \
		--infodir=/usr/share/info \
		$(E2FSPROGS_OPTS) \
		$(DISABLE_NLS) \
		$(DISABLE_LARGEFILE) \
	)
	touch $@

$(E2FSPROGS_DIR)/$(E2FSPROGS_BINARY): $(E2FSPROGS_DIR)/.configured
	$(MAKE1) -C $(E2FSPROGS_DIR)
	touch -c $@

#$(E2FSPROGS_DIR)/lib/$(LIBUUID_TARGET_BINARY): $(E2FSPROGS_DIR)/.configured
#	$(MAKE1) -C $(E2FSPROGS_DIR)/lib/uuid
#	touch -c $@
# 
# $(STAGING_DIR)/$(E2FSPROGS_TARGET_BINARY): $(E2FSPROGS_DIR)/$(E2FSPROGS_BINARY)
# 	$(MAKE1) PATH=$(TARGET_PATH) DESTDIR=$(STAGING_DIR) LDCONFIG=true \
# 		-C $(E2FSPROGS_DIR) install install-libs
# 
# $(STAGING_DIR)/$(LIBUUID_TARGET_DIR)/$(LIBUUID_TARGET_BINARY): $(E2FSPROGS_DIR)/lib/$(LIBUUID_TARGET_BINARY)
# 	$(MAKE1) PATH=$(TARGET_PATH) DESTDIR=$(STAGING_DIR) LDCONFIG=true \
# 		-C $(LIBUUID_DIR) install

#$(TARGET_DIR)/$(E2FSPROGS_TARGET_BINARY): $(STAGING_DIR)/$(E2FSPROGS_TARGET_BINARY)
$(TARGET_DIR)/$(E2FSPROGS_TARGET_BINARY): $(E2FSPROGS_DIR)/$(E2FSPROGS_BINARY)
	$(MAKE1) -C $(E2FSPROGS_DIR) DESTDIR=$(STAGING_DIR) install-libs
	$(MAKE1) -C $(E2FSPROGS_DIR) DESTDIR=$(TARGET_DIR) install
# 	rm -rf ${TARGET_DIR}/sbin/mkfs.ext[234] \
# 		${TARGET_DIR}/sbin/fsck.ext[234] \
# 		${TARGET_DIR}/sbin/findfs \
# 		${TARGET_DIR}/sbin/tune2fs
ifneq ($(BR2_PACKAGE_E2FSPROGS_EXTRA),y)
	( cd $(TARGET_DIR); rm -f $(E2FSPROGS_EXTRA_BIN) )
endif
# ifneq ($(BR2_HAVE_INFOPAGES),y)
# 	rm -rf $(TARGET_DIR)/usr/share/info
# endif
# ifneq ($(BR2_HAVE_MANPAGES),y)
# 	rm -rf $(TARGET_DIR)/usr/share/man
# endif
# 	rm -rf $(TARGET_DIR)/share/locale
# 	rm -rf $(TARGET_DIR)/usr/share/doc
	touch -c $@

# $(TARGET_DIR)/$(LIBUUID_TARGET_DIR)/$(LIBUUID_TARGET_BINARY): $(STAGING_DIR)/$(LIBUUID_TARGET_DIR)/$(LIBUUID_TARGET_BINARY)
# 	$(MAKE1) PATH=$(TARGET_PATH) DESTDIR=$(STAGING_DIR) LDCONFIG=true \
# 		-C $(LIBUUID_DIR) install
# 	cp -a $(STAGING_DIR)/$(LIBUUID_TARGET_DIR)/$(LIBUUID_TARGET_BINARY)* \
# 		$(TARGET_DIR)/$(LIBUUID_TARGET_DIR)/
# 	touch $@

e2fsprogs: uclibc $(TARGET_DIR)/$(E2FSPROGS_TARGET_BINARY)

e2fsprogs-build: $(E2FSPROGS_DIR)/$(E2FSPROGS_BINARY)

e2fsprogs-configure: $(E2FSPROGS_DIR)/.configured

e2fsprogs-clean:
	$(MAKE1) DESTDIR=$(TARGET_DIR) CC=$(TARGET_CC) -C $(E2FSPROGS_DIR) uninstall
	-$(MAKE1) -C $(E2FSPROGS_DIR) clean

e2fsprogs-dirclean:
	rm -rf $(E2FSPROGS_DIR)

# several other packages depends on this target
libuuid: e2fsprogs

#libuuid: $(TARGET_DIR)/$(LIBUUID_TARGET_DIR)/$(LIBUUID_TARGET_BINARY)

# libuuid-clean:
# 	-$(MAKE1) PATH=$(TARGET_PATH) DESTDIR=$(STAGING_DIR) LDCONFIG=true \
# 		-C $(LIBUUID_DIR) uninstall
# 	# make uninstall misses the includes
# 	rm -rf $(STAGING_DIR)/usr/include/uuid
# 	rm -f $(TARGET_DIR)/$(LIBUUID_TARGET_DIR)/$(LIBUUID_TARGET_BINARY)*
# 	-$(MAKE1) -C $(LIBUUID_DIR) clean
# 
#libuuid-source: e2fsprogs-source
#libuuid-dirclean: e2fsprogs-dirclean

#############################################################
#
# Toplevel Makefile options
#
#############################################################
ifeq ($(BR2_PACKAGE_E2FSPROGS),y)
TARGETS+=e2fsprogs
endif

#ifeq ($(BR2_PACKAGE_LIBUUID),y)
#TARGETS+=libuuid
#endif
