#!/bin/bash


ANSIBLE_HOME="$HOME/.ansible"

[ ! -d "$ANSIBLE_HOME" ] && mkdir "$ANSIBLE_HOME"



prepare() {
    # Copy config file
    cp "test/ansible-inventory.cfg" "$HOME/.ansible/"

    # Copy test inventory
    cp "test/ansible_test_inventory.json" "/tmp"
}


exec_cmd() {
    cmd="$*"

    echo "------------------------------------------------"
    echo "¬¬ ./ansible-inventory --batch \"$cmd\""
    output="$(./ansible-inventory --batch "$cmd")"
    retcode="$?"
    echo "$output"
    echo

    echo "$output" | egrep -q '\^   error' && return 1
    echo "$output" | egrep -q '*** Unknown syntax:' && return 1

    return "$retcode"
}

run_test(){
    exec_cmd $*
    [ "$?" != 0 ] && do_exit 1
}

do_exit(){
    rm -f "/tmp/ansible_test_inventory.json"
    exit $1
}



ai_tests=(
    'show hosts'
    'show hosts d.*'
    'show hosts asdfasdd.*'
    'show groups'
    'show groups v.*'
    'show groups asdfasdd.*'
    'show tree vp1_our1'
    'add host test1'
    'add host name=test2'
    'add host name=test3 host=1.2.3.4:2222'
    'add host name=test4 host=:2222'
    'add host name=test5 host=1.2.3.4'
    'add host test1 to_groups=vp1_our1'
    'add host test.* to_groups=vp1.*,vp2.*'
    'add group gtest1'
    'add group gtest1 to_groups=vp1.*,vp2.*'
    'add var k1=v1 to_hosts=test.*,n.*,d.*'
    'add var k2=v2 to_groups=vp1.*,vp2.*'
    'edit host test1 new_name=htest1'
    'edit host htest1 new_host=1.2.3.4:2222'
    'edit host htest1 new_host=:2222'
    'edit host htest1 new_host=1.2.3.4'
    'edit group gtest1 new_name=group1test'
    'edit var k1 new_name=key1 in_hosts=d.*,g.*,n.*'
    'edit var key1 new_value=value1 in_groups=vp1.*'
    'del var key1 from_hosts=d.*,g.*,n.*'
    'del var key1 from_groups=vp1.*,vp2.*'
    'del host test.* from_groups=vp1.*,vp2.*'
    'del host htest1'
    'del host test.*'
    'del group gtest1 from_groups=vp1.*,vp2.*'
    'del group gtest1'
    'del group vp1.*,vp2.*'
)


prepare

for test in "${ai_tests[@]}"; do
    echo "y" | run_test "$test"
done

do_exit 0
