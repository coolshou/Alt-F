#!/bin/sh

. common.sh
check_cookie

SSL_DIR=/etc/ssl/certs

BOX_CA_KEY=$SSL_DIR/rootCA.key
BOX_CA_CRT=$SSL_DIR/rootCA.crt
BOX_CA_PEM=$SSL_DIR/rootCA.pem

BOX_PEM=$SSL_DIR/server.pem
BOX_CRT=$SSL_DIR/server.crt
BOX_KEY=$SSL_DIR/server.key
BOX_CSR=$SSL_DIR/server.csr
BOX_CNF=/etc/ssl/server.cnf

MISC_CONF=/etc/misc.conf
CONF_LIGHTY=/etc/lighttpd/lighttpd.conf

PORT_CHECKER=https://www.canyouseeme.org

ACME_CONF=/etc/acme.sh
#ACME_MODE="--test"
if test -z "$ACME_MODE"; then
	INST_DIR=$SSL_DIR
else
	INST_DIR=/etc/lighttpd/certs
fi

if ! test -d /Alt-F/$SSL_DIR; then
	aufs.sh -n
	mkdir -p /Alt-F/$SSL_DIR
	aufs.sh -r
fi

ext_domain=$(httpd -d "$ext_domain")

# $1-external port
canyouseeme() {
	if test "$1" -gt 0; then
		ok_res='color="green"><b>Success:</b>'
		#err_res='color="red"><b>Error:</b>'
		if wget -q --post-data port=$1 -O - $PORT_CHECKER | grep -q "$ok_res"; then
			return 0
		fi
	fi
	return 1
}

#umask 077

if test "${CONTENT_TYPE%;*}" = "multipart/form-data"; then
	if ! res=$(upload_file); then
		msg "Error: Uploading failed."
	fi
	#echo res="$res"
	eval "$res"
else
	read_args
fi

#debug

if test -n "$ProtectKey"; then
	if test -z "$pass1"; then
		msg "The password can't be empty."
	elif test "$pass1" != "$pass2"; then
		msg "The two passwords don't match."
	fi

	if ! pass1=$(checkpass "$pass1"); then
    	msg "$pass1"
	fi
	
	echo "$pass1" | openssl rsa -des3 -in $BOX_CA_KEY -out $BOX_CA_KEY-tmp -passout stdin >& /dev/null
	mv $BOX_CA_KEY-tmp $BOX_CA_KEY	

elif test -n "$CRTexport"; then
	download_file $BOX_CA_CRT Alt-F-fake-rootCA.crt
	exit 0

elif test -n "$CAsave"; then
	cat $BOX_CA_KEY $BOX_CA_CRT > $BOX_CA_PEM
	download_file $BOX_CA_PEM Alt-F-fake-rootCA.pem
	rm $BOX_CA_PEM
	exit 0
	
elif test -n "$CAload"; then
	if test -z "$pass"; then
		rm -f $CAload2
		msg "Error, you have to supply the password of the file private key to load."
	fi
	
	if ! pass=$(checkpass "$pass"); then
		rm -f $CAload2
    	msg "$pass"
	fi
	
	if ! test -s $CAload2; then
		rm -f $CAload2
		msg "Error, empty file uploaded."
	fi
	
	mv $CAload2 $BOX_CA_PEM
	sed -n '/BEGIN CERTIFICATE/,/END CERTIFICATE/p' $BOX_CA_PEM > $BOX_CA_CRT-tmp
	sed -n '/BEGIN .*PRIVATE KEY/,/END .*PRIVATE KEY/p' $BOX_CA_PEM > $BOX_CA_KEY-tmp
	rm -f $BOX_CA_PEM

	if ! test -s $BOX_CA_KEY-tmp -a -s $BOX_CA_KEY-tmp; then
		rm -f $BOX_CA_KEY-tmp $BOX_CA_CRT-tmp
		msg "Error, the key and certificate, in DEM format, must be concatenated together in the file to upload."
	fi
	
	# verify key consistency
	if ! echo "$pass" | openssl rsa -passin stdin -in $BOX_CA_KEY-tmp \
		-check -noout >& /dev/null; then
			rm -f $BOX_CA_KEY-tmp $BOX_CA_CRT-tmp
			msg "Error, wrong key password or private key is inconsistent."
	fi

# Another way to check the private key and cert pub key, is to sign a message
# with the private key and then verify it with the public key. You could do it like this:
# openssl x509 -in [certificate] -noout -pubkey > pubkey.pem
# dd if=/dev/urandom of=rnd bs=32 count=1
# openssl rsautl -sign -pkcs -inkey [privatekey] -in rnd -out sig
# openssl rsautl -verify -pkcs -pubin -inkey pubkey.pem -in sig -out check
# cmp rnd check
# rm rnd check sig pubkey.pem
# https://blog.hboeck.de/archives/888-How-I-tricked-Symantec-with-a-Fake-Private-Key.html

	# verify public keys are identical in cert and key
	crtck=$(openssl x509 -in $BOX_CA_CRT-tmp -pubkey | \
		openssl pkey -pubin -pubout -outform der | sha256sum)
	
	keyck=$(echo "$pass" | openssl pkey -passin stdin -in $BOX_CA_KEY-tmp -pubout -outform der | sha256sum)
	
	if ! test "$crtck" = "$keyck"; then		
		rm -f $BOX_CA_KEY-tmp $BOX_CA_CRT-tmp
		msg "Error, key and certificate public keys don't match."
	fi

	mv $BOX_CA_KEY-tmp $BOX_CA_KEY
	mv $BOX_CA_CRT-tmp $BOX_CA_CRT
	chmod a+r $BOX_CA_CRT

elif test -n "$createCA"; then
	nbits=$(httpd -d "$nbits")
	
	if test "$SSL_CERT_BITS" != "$nbits"; then
		sed -i '/^SSL_CERT_BITS=/d' $MISC_CONF
		echo "SSL_CERT_BITS=\"$nbits\"" >> $MISC_CONF
		SSL_CERT_BITS=$nbits
	fi
	
	export HOST=$(hostname) HOSTFQDN=$(hostname -f) HOSTIP=$(hostname -i) \
		DOMAIN=$(hostname -d) BOX=$(cat /tmp/board) REQNAME=req_dname_ca SSL_CERT_BITS
		
	openssl req -x509 -new -nodes -sha256 -days 7300 -newkey rsa -keyout $BOX_CA_KEY \
		-out $BOX_CA_CRT -extensions v3_ca -config $BOX_CNF >& /dev/null
	
elif test -n "$createCert"; then
	if test -z "$pass"; then
		msg "Error, you have to supply the password of the CA private key."
	fi
	
	if ! pass=$(checkpass "$pass"); then
    	msg "$pass"
	fi
	
	rm -f $BOX_KEY $BOX_CRT $BOX_PEM
	
	if test -z "$SSL_CERT_BITS"; then
		SSL_CERT_BITS=2048
		sed -i '/^SSL_CERT_BITS=/d' $MISC_CONF
		echo "SSL_CERT_BITS=\"$SSL_CERT_BITS\"" >> $MISC_CONF
	fi
	
	export HOST=$(hostname) HOSTFQDN=$(hostname -f) HOSTIP=$(hostname -i) \
		DOMAIN=$(hostname -d) BOX=$(cat /tmp/board) REQNAME=req_dname SSL_CERT_BITS=$SSL_CERT_BITS

	# create box private key and sign request in one step
	openssl req -new -nodes -sha256 -newkey rsa \
		-keyout $BOX_KEY -out $BOX_CSR -config $BOX_CNF >& /dev/null

	# CA sign the certificate sign request
	echo "$pass" | openssl x509 -req -days 365 -sha256 \
		-CA $BOX_CA_CRT -CAkey $BOX_CA_KEY -CAcreateserial -passin stdin \
		-in $BOX_CSR -out $BOX_CRT -extensions v3_req -extfile $BOX_CNF >& /dev/null
	cat $BOX_KEY $BOX_CRT > $BOX_PEM
	rcstunnel reload >& /dev/null # FIXME: browser complains cert changed, has to reload page

elif test -n "$selfSignCert"; then
	rm -f $BOX_KEY $BOX_CRT $BOX_PEM
	
	if test -z "$SSL_CERT_BITS"; then
		SSL_CERT_BITS=2048
		sed -i '/^SSL_CERT_BITS=/d' $MISC_CONF
		echo "SSL_CERT_BITS=\"$SSL_CERT_BITS\"" >> $MISC_CONF
	fi
	
	export HOST=$(hostname) HOSTFQDN=$(hostname -f) HOSTIP=$(hostname -i) \
		DOMAIN=$(hostname -d) BOX=$(cat /tmp/board) REQNAME=req_dname SSL_CERT_BITS=$SSL_CERT_BITS

	# create box private key and cert and selfsign in one step
	openssl req -x509 -nodes -sha256 -days 365 -newkey rsa -keyout $BOX_KEY -out $BOX_CRT \
		-extensions v3_req -config $BOX_CNF >& /dev/null
	cat $BOX_KEY $BOX_CRT > $BOX_PEM
	rcstunnel reload >& /dev/null # FIXME: browser complains cert changed, has to reload page

elif test -n "$getCert"; then		
	html_header "Requesting a Let's Encrypt certificate"
	busy_cursor_start
	
	# double "$@" expansion in /usr/bin/acme.sh and acme.sh itself is not working... repeat
	if canyouseeme 80 >& /dev/null; then
		echo "<p><strong>Port 80 visible from the internet, requesting certificate:</strong></p><pre>"
		server_root=$(httpd -d $server_root)

		if ! acme.sh $ACME_MODE --issue --webroot $server_root/htdocs \
			--domain $ext_domain \
			--reloadcmd "rclighttpd restart" \
			--cert-file $INST_DIR/$ext_domain.crt \
			--key-file $INST_DIR/$ext_domain.key \
			--ca-file $INST_DIR/$ext_domain-ca.crt; then
			msg "Error obtaining certificate from Let's Encrypt, for details see the acme.sh log."
		fi

	elif canyouseeme 443 >& /dev/null; then
		echo "<p><strong>Port 443 visible from the internet, requesting certificate:</strong></p><pre>"
		alpndir=$(sed -n 's|^var.alpn_dir[[:space:]]*=[[:space:]]*"\(.*\)".*|\1|p' $CONF_LIGHTY)
		
		if ! acme.sh $ACME_MODE --issue --alpn $alpndir \
			--domain $ext_domain \
			--reloadcmd "rclighttpd restart" \
			--cert-file $INST_DIR/$ext_domain.crt \
			--key-file $INST_DIR/$ext_domain.key \
			--ca-file $INST_DIR/$ext_domain-ca.crt; then
			msg "Error obtaining certificate from Let's Encrypt, for details see the acme.sh log."
		fi
	else
		msg "Neither external port 80 nor port 443 can be seen from the internet. Check the router port forwarding on the lighttpd configuration."
	fi

	MAIL_FROM=$(httpd -d "$MAIL_FROM")
	MAIL_TO=$(httpd -d "$MAIL_TO")
	export MAIL_FROM MAIL_TO MAIL_BIN="/usr/bin/mail"
	
	echo "</pre><p><strong>Got certificate, now setting notify e-mail address and renew cronjob:</strong></p><pre>"
	if ! acme.sh $ACME_MODE --set-notify --notify-hook mail; then
		msg "acme.sh set notify error, for details see the acme.sh log."
	fi

	acme.sh --install-cronjob
	
	busy_cursor_end
	echo "</pre><p><strong>Sucess</strong> $(goto_button Continue /cgi-bin/certs.cgi)</p></body></html>"
	exit 0

elif test -n "$renewCert"; then
	html_header "Renewing Let's Encrypt certificate"
	busy_cursor_start
	
	echo "<pre>"
	if ! acme.sh $ACME_MODE --renew --force --domain $ext_domain ; then
		msg "Error renewing certificate, for details see the acme.sh log."
	fi
	
	busy_cursor_end
	echo "</pre><p><strong>Sucess</strong> $(goto_button Continue /cgi-bin/certs.cgi)</p></body></html>"
	exit 0

elif test -n "$revokeCert"; then
	html_header "Revoking Let's Encrypt certificate"
	busy_cursor_start

	echo "<pre>"
	if ! acme.sh $ACME_MODE --revoke --domain $ext_domain; then
		msg "Error revoking certificate, for details see the acme.sh log."
	fi
	# only ${ext_domain}.cer is removed from /etc/acme.sh/$ext_domain? is that it?
	rm -rf $ACME_CONF/$ext_domain $INST_DIR/${ext_domain}*

	busy_cursor_end
	echo "</pre><p><strong>Sucess</strong> $(goto_button Continue /cgi-bin/certs.cgi)</p></body></html>"
	exit 0

	
elif test -n "$removeCert"; then
	busy_cursor_start

	if ! acme.sh $ACME_MODE --remove --domain $ext_domain >& /dev/null; then
		msg "Error removing certificate, for details see the acme.sh log."
	fi
	rm -rf $ACME_CONF/$ext_domain $INST_DIR/${ext_domain}*
fi

#enddebug
js_gotopage /cgi-bin/certs.cgi
