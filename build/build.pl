#!/usr/bin/perl

# Copyright 2023 Nils Knieling. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

use strict;
use JSON::XS;
use Template;
use File::Copy;

my $roles_json              = "roles.json";
my $permissions_csv         = "permissions.csv";
my $export_roles_json       = "../page/roles.json";
my $export_permissions_json = "../page/permissions.json";

print "Please wait...\n";

# JSON

mkdir('../page/');

open(ROLES, '>', $export_roles_json) or die $!;
open(PERMISSION, '>', $export_permissions_json) or die $!;

open(ROLES_JSON, '<', $roles_json) or die $!;
my $json = "";
while (my $row = <ROLES_JSON>) {
	chomp $row;
	$json .= $row;
}
my $roles_scalar = JSON::XS->new->utf8->decode($json);

my %permission_roles_hash = {};
my %role_permissions_hash = {};
open(PERMISSIONS_CSV, '<', $permissions_csv) or die $!;
while (my $row = <PERMISSIONS_CSV>) {
	chomp $row;
	my @role = split(";", $row);
	my $role_name = $role[0];
	my $role_permissions  = $role[1];
	next if ($role_name eq "name"); # Skip header
	my @permissions = split(",", $role_permissions);
	my @permissions_name = ();
	foreach my $permission_name (sort @permissions) {
		push(@permissions_name, {name => $permission_name });
	}
	$role_permissions_hash{$role_name} = \@permissions_name;

	foreach my $permission_name (sort @permissions) {
		push(@{$permission_roles_hash{$permission_name}}, $role_name);
	}
}

my @roles_list = ();
foreach my $role (@{$roles_scalar}) {
	my $role_name        = $role->{'name'}        || '???';
	my $role_title       = $role->{'title'}       || '???';
	my $role_description = $role->{'description'} || '-';
	my $role_stage       = $role->{'stage'}       || '?';
	$role_description =~ s/^\s//; # Remove beginning white space
	push(@roles_list, {
		name        => $role_name,
		title       => $role_title,
		desc        => $role_description,
		stage       => $role_stage,
		permissions => $role_permissions_hash{$role_name}
	});
}

my @permissions_list = ();
foreach my $permission_name (keys %permission_roles_hash) {
	my @roles_name = ();
	foreach my $permission_role (@{$permission_roles_hash{$permission_name}}) {
		foreach my $role (@{$roles_scalar}) {
			if ($permission_role eq $role->{'name'}) {
				my $role_name        = $role->{'name'}        || '???';
				my $role_title       = $role->{'title'}       || '???';
				my $role_description = $role->{'description'} || '-';
				my $role_stage       = $role->{'stage'}       || '?';
				push(@roles_name, {
					name        => $role_name,
					title       => $role_title,
					desc        => $role_description,
					stage       => $role_stage
				});
			}
		}
	}
	push(@permissions_list, {
		name  => $permission_name,
		roles => \@roles_name
	});
}

my $export_roles_json = JSON::XS->new->utf8->encode(\@roles_list);
print ROLES $export_roles_json;

my $permission_json = JSON::XS->new->utf8->encode(\@permissions_list);
print PERMISSION $permission_json;

# PAGE

my $gmttime   = gmtime();
my $timestamp = time();

my $template = Template->new(
	INCLUDE_PATH => './src',
	PRE_PROCESS  => 'config.tt2',
	VARIABLES => {
		'gmttime'          => $gmttime,
		'timestamp'        => $timestamp,
		'gitHubServerUrl'  => $ENV{'GITHUB_SERVER_URL'} || '',
		'gitHubRepository' => $ENV{'GITHUB_REPOSITORY'} || '',
		'gitHubRunId'      => $ENV{'GITHUB_RUN_ID'}     || '',
	}
);

$template->process('index.tt2',       { 'roles' => \@roles_list },             '../page/index.html')       || die "Template process failed: ", $template->error(), "\n";
$template->process('permissions.tt2', { 'permissions' => \@permissions_list }, '../page/permissions.html') || die "Template process failed: ", $template->error(), "\n";
$template->process('robots.txt',      {},                                      '../page/robots.txt')       || die "Template process failed: ", $template->error(), "\n";
$template->process('404.tt2',         {},                                      '../page/404.html')         || die "Template process failed: ", $template->error(), "\n";

copy('./src/img/favicon/favicon.ico',          '../page/favicon.ico');
copy('./src/img/favicon/favicon-16x16.png',    '../page/favicon-16x16.png');
copy('./src/img/favicon/favicon-32x32.png',    '../page/favicon-32x32.png');
copy('./src/img/favicon/apple-touch-icon.png', '../page/apple-touch-icon.png');

print "DONE\n";